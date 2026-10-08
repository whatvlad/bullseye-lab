from __future__ import annotations

import asyncio
import base64
import binascii
from collections.abc import Awaitable, Callable
from decimal import Decimal

from memebot.core.clock import utc_now
from memebot.providers.solana.base import Commitment, RpcAccount, SolanaRpcProvider
from memebot.providers.solana.encoding import BorshDecodeError
from memebot.providers.solana.pump_idl import (
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    MintAccountState,
    decode_bonding_curve_account,
    decode_mint_account,
    decode_pool_account,
    decode_token_account,
)
from memebot.providers.solana.rpc import SolanaRpcError

from .models import LocalRiskContext, OnChainRiskFacts


class SolanaRiskCollector:
    """Collect read-only, reproducible risk facts from standard Solana RPC."""

    def __init__(
        self,
        rpc: SolanaRpcProvider,
        *,
        commitment: Commitment,
        retry_count: int = 1,
        retry_delay_seconds: float = 0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._rpc = rpc
        self._commitment = commitment
        self._retry_count = max(1, retry_count)
        self._retry_delay_seconds = max(0, retry_delay_seconds)
        self._sleep = sleep

    async def collect(self, context: LocalRiskContext) -> OnChainRiskFacts:
        slots = [context.source_slot or 0]
        mint_state = None
        mint_error = None
        market_account: RpcAccount | None = None
        market_error: str | None = None

        try:
            mint_account = await self._rpc_call(
                lambda: self._rpc.get_account(context.mint, self._commitment)
            )
            if mint_account is None:
                mint_error = "mint_account_not_found"
            elif mint_account.owner not in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}:
                mint_error = "mint_account_owner_not_token_program"
            else:
                slots.append(mint_account.slot)
                mint_state = decode_mint_account(_account_data(mint_account))
        except (SolanaRpcError, BorshDecodeError, binascii.Error, ValueError) as error:
            mint_error = _error_code(error, "mint_account_unreadable")

        if context.market is None:
            market_error = "market_address_unknown"
        else:
            market = context.market
            try:
                market_account = await self._rpc_call(
                    lambda: self._rpc.get_account(market, self._commitment)
                )
                if market_account is None:
                    market_error = "market_account_not_found"
                else:
                    slots.append(market_account.slot)
            except SolanaRpcError as error:
                market_error = error.code

        (
            top1,
            top5,
            top10,
            holder_error,
            excluded_market_accounts,
            circulating_supply,
        ) = await self._holder_distribution(context, mint_state, market_account, slots)
        creator_holding, creator_error = await self._creator_holding(
            context, circulating_supply, holder_error, slots
        )
        available_quote, liquidity_error = await self._liquidity(
            market_account, market_error, slots
        )

        return OnChainRiskFacts(
            observed_at=utc_now(),
            source_slot=max(slots),
            mint_state=mint_state,
            mint_error=mint_error,
            top1_holder_percent=top1,
            top5_holder_percent=top5,
            top10_holder_percent=top10,
            holder_error=holder_error,
            circulating_supply_raw=circulating_supply,
            creator_holding_percent=creator_holding,
            creator_holding_error=creator_error,
            available_quote_reserves_raw=available_quote,
            liquidity_error=liquidity_error,
            excluded_market_token_accounts=excluded_market_accounts,
        )

    async def _holder_distribution(
        self,
        context: LocalRiskContext,
        mint_state: MintAccountState | None,
        market_account: RpcAccount | None,
        slots: list[int],
    ) -> tuple[
        Decimal | None,
        Decimal | None,
        Decimal | None,
        str | None,
        int,
        int | None,
    ]:
        if mint_state is None:
            return None, None, None, "mint_supply_unknown", 0, None
        if market_account is None or context.market is None:
            return None, None, None, "market_account_unknown_for_exclusion", 0, None

        try:
            largest = await self._rpc_call(
                lambda: self._rpc.get_token_largest_accounts(context.mint, self._commitment)
            )
            slots.append(largest.slot)
            addresses = [balance.address for balance in largest.balances]
            accounts = await self._rpc_call(
                lambda: self._rpc.get_multiple_accounts(addresses, self._commitment)
            )
            explicit_market_accounts = _explicit_market_token_accounts(market_account)
            retained: list[int] = []
            excluded_amount = 0
            excluded_count = 0
            for balance, account in zip(largest.balances, accounts, strict=True):
                if account is None:
                    raise ValueError("largest_token_account_not_found")
                slots.append(account.slot)
                decoded = decode_token_account(_account_data(account))
                if decoded.mint != context.mint:
                    raise ValueError("largest_token_account_mint_mismatch")
                if decoded.owner == context.market or balance.address in explicit_market_accounts:
                    excluded_amount += balance.amount_raw
                    excluded_count += 1
                else:
                    retained.append(balance.amount_raw)

            supply = mint_state.supply
            circulating = supply - excluded_amount
            if circulating <= 0:
                return (
                    None,
                    None,
                    None,
                    "circulating_supply_not_positive",
                    excluded_count,
                    None,
                )
            retained.sort(reverse=True)
            return (
                _share(sum(retained[:1]), circulating),
                _share(sum(retained[:5]), circulating),
                _share(sum(retained[:10]), circulating),
                None,
                excluded_count,
                circulating,
            )
        except (SolanaRpcError, BorshDecodeError, binascii.Error, ValueError) as error:
            return (
                None,
                None,
                None,
                _error_code(error, "holder_distribution_unreadable"),
                0,
                None,
            )

    async def _creator_holding(
        self,
        context: LocalRiskContext,
        circulating_supply: int | None,
        holder_error: str | None,
        slots: list[int],
    ) -> tuple[Decimal | None, str | None]:
        if context.creator is None:
            return None, "creator_address_unknown"
        creator = context.creator
        if holder_error is not None:
            return None, "circulating_supply_unknown"
        if circulating_supply is None or circulating_supply <= 0:
            return None, "circulating_supply_not_positive"
        try:
            balances = await self._rpc_call(
                lambda: self._rpc.get_token_accounts_by_owner(
                    creator, context.mint, self._commitment
                )
            )
            slots.append(balances.slot)
            return (
                _share(
                    sum(item.amount_raw for item in balances.balances),
                    circulating_supply,
                ),
                None,
            )
        except SolanaRpcError as error:
            return None, error.code

    async def _liquidity(
        self,
        market_account: RpcAccount | None,
        market_error: str | None,
        slots: list[int],
    ) -> tuple[int | None, str | None]:
        if market_account is None:
            return None, market_error or "market_account_unknown"
        try:
            if market_account.owner == PUMP_PROGRAM_ID:
                curve = decode_bonding_curve_account(_account_data(market_account))
                return curve.real_quote_reserves + curve.virtual_quote_reserves, None
            if market_account.owner == PUMP_AMM_PROGRAM_ID:
                pool = decode_pool_account(_account_data(market_account))
                quote_account = await self._rpc_call(
                    lambda: self._rpc.get_account(pool.pool_quote_token_account, self._commitment)
                )
                if quote_account is None:
                    return None, "pool_quote_token_account_not_found"
                slots.append(quote_account.slot)
                quote_balance = decode_token_account(_account_data(quote_account))
                if quote_balance.mint != pool.quote_mint:
                    return None, "pool_quote_token_account_mint_mismatch"
                effective = quote_balance.amount + pool.virtual_quote_reserves
                if effective < 0:
                    return None, "pool_effective_quote_reserves_negative"
                return effective, None
            return None, "unsupported_market_program"
        except (SolanaRpcError, BorshDecodeError, binascii.Error, ValueError) as error:
            return None, _error_code(error, "liquidity_unreadable")

    async def _rpc_call[ValueT](self, operation: Callable[[], Awaitable[ValueT]]) -> ValueT:
        for attempt in range(self._retry_count):
            try:
                return await operation()
            except SolanaRpcError as error:
                if not error.rate_limited or attempt + 1 >= self._retry_count:
                    raise
                await self._sleep(self._retry_delay_seconds * (2**attempt))
        raise RuntimeError("unreachable_rpc_retry_state")


def _account_data(account: RpcAccount) -> bytes:
    return base64.b64decode(account.data_base64, validate=True)


def _explicit_market_token_accounts(account: RpcAccount) -> set[str]:
    if account.owner != PUMP_AMM_PROGRAM_ID:
        return set()
    pool = decode_pool_account(_account_data(account))
    return {pool.pool_base_token_account}


def _share(amount: int, supply: int) -> Decimal:
    return (Decimal(amount) * Decimal(100) / Decimal(supply)).quantize(Decimal("0.0001"))


def _error_code(error: Exception, fallback: str) -> str:
    if isinstance(error, SolanaRpcError):
        return error.code
    message = str(error).strip()
    return message if message else fallback
