import base64
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from memebot.intelligence.risk.collector import SolanaRiskCollector
from memebot.intelligence.risk.models import LocalRiskContext, OnChainRiskFacts
from memebot.intelligence.risk.rules import RiskAssessor, RiskPolicy
from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.providers.solana.base import RpcAccount, RpcHealth, RpcTokenBalance, RpcTokenBalances
from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.pump_idl import (
    BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
    PUMP_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    MintAccountState,
)
from memebot.providers.solana.rpc import SolanaRpcError


def _key(seed: int) -> tuple[bytes, str]:
    raw = bytes([seed]) * 32
    return raw, encode_base58(raw)


MINT_RAW, MINT = _key(1)
MARKET_RAW, MARKET = _key(2)
CREATOR_RAW, CREATOR = _key(3)
HOLDER_RAW, HOLDER = _key(4)
MARKET_TOKEN_RAW, MARKET_TOKEN = _key(5)
HOLDER_TOKEN_RAW, HOLDER_TOKEN = _key(6)
SECOND_TOKEN_RAW, SECOND_TOKEN = _key(7)
QUOTE_RAW, _QUOTE = _key(8)
NOW = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)


def _account(address: str, owner: str, data: bytes, slot: int = 100) -> RpcAccount:
    return RpcAccount(
        address=address,
        slot=slot,
        owner=owner,
        lamports=1,
        executable=False,
        data_base64=base64.b64encode(data).decode(),
    )


def _mint_data(supply: int) -> bytes:
    return b"".join(
        [
            (0).to_bytes(4, "little"),
            bytes(32),
            supply.to_bytes(8, "little"),
            b"\x06\x01",
            (0).to_bytes(4, "little"),
            bytes(32),
        ]
    )


def _token_data(owner: bytes, amount: int) -> bytes:
    return MINT_RAW + owner + amount.to_bytes(8, "little")


def _curve_data() -> bytes:
    return b"".join(
        [
            BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
            (500).to_bytes(8, "little"),
            (40).to_bytes(8, "little"),
            (400).to_bytes(8, "little"),
            (20).to_bytes(8, "little"),
            (1000).to_bytes(8, "little"),
            b"\x00",
            CREATOR_RAW,
            b"\x00\x00",
            QUOTE_RAW,
        ]
    )


class FakeRpc:
    async def health(self) -> RpcHealth:
        raise NotImplementedError

    async def get_account(self, address: str, commitment: str) -> RpcAccount | None:
        del commitment
        if address == MINT:
            return _account(MINT, TOKEN_PROGRAM_ID, _mint_data(1000))
        if address == MARKET:
            return _account(MARKET, PUMP_PROGRAM_ID, _curve_data())
        return None

    async def get_transaction(self, signature: str, commitment: str) -> dict[str, object] | None:
        raise NotImplementedError

    async def get_multiple_accounts(
        self, addresses: list[str], commitment: str
    ) -> tuple[RpcAccount | None, ...]:
        del commitment
        accounts = {
            MARKET_TOKEN: _account(MARKET_TOKEN, TOKEN_PROGRAM_ID, _token_data(MARKET_RAW, 600)),
            HOLDER_TOKEN: _account(HOLDER_TOKEN, TOKEN_PROGRAM_ID, _token_data(HOLDER_RAW, 250)),
            SECOND_TOKEN: _account(
                SECOND_TOKEN, TOKEN_PROGRAM_ID, _token_data(bytes([9]) * 32, 150)
            ),
        }
        return tuple(accounts[address] for address in addresses)

    async def get_token_largest_accounts(self, mint: str, commitment: str) -> RpcTokenBalances:
        del mint, commitment
        return RpcTokenBalances(
            slot=101,
            balances=(
                RpcTokenBalance(address=MARKET_TOKEN, amount_raw=600),
                RpcTokenBalance(address=HOLDER_TOKEN, amount_raw=250),
                RpcTokenBalance(address=SECOND_TOKEN, amount_raw=150),
            ),
        )

    async def get_token_accounts_by_owner(
        self, owner: str, mint: str, commitment: str
    ) -> RpcTokenBalances:
        del owner, mint, commitment
        return RpcTokenBalances(
            slot=102, balances=(RpcTokenBalance(address=HOLDER_TOKEN, amount_raw=50),)
        )

    async def close(self) -> None:
        return None


class RateLimitedRpc(FakeRpc):
    def __init__(self) -> None:
        self.largest_attempts = 0

    async def get_token_largest_accounts(self, mint: str, commitment: str) -> RpcTokenBalances:
        self.largest_attempts += 1
        if self.largest_attempts < 3:
            raise SolanaRpcError("http_429", rate_limited=True)
        return await super().get_token_largest_accounts(mint, commitment)


def _context() -> LocalRiskContext:
    return LocalRiskContext(
        mint=MINT,
        creator=CREATOR,
        market=MARKET,
        quote_mint=_QUOTE,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        observed_at=NOW,
        source_slot=99,
        creator_launches=1,
        creator_graduations=0,
        creator_rejections=0,
        early_unique_buyers=2,
        largest_early_buyer_share_percent=Decimal("45"),
        largest_synchronized_buyer_group=2,
    )


def _policy() -> RiskPolicy:
    return RiskPolicy(
        top1_hard_reject_percent=Decimal("40"),
        top5_warning_percent=Decimal("60"),
        top10_warning_percent=Decimal("80"),
        creator_hard_reject_percent=Decimal("20"),
        largest_buyer_warning_percent=Decimal("50"),
        synchronized_buyers_warning_count=3,
    )


@pytest.mark.asyncio
async def test_collector_excludes_market_balance_and_reads_curve_liquidity() -> None:
    collector = SolanaRiskCollector(FakeRpc(), commitment="confirmed")  # type: ignore[arg-type]

    facts = await collector.collect(_context())

    assert facts.holder_error is None
    assert facts.circulating_supply_raw == 400
    assert facts.excluded_market_token_accounts == 1
    assert facts.top1_holder_percent == Decimal("62.5000")
    assert facts.creator_holding_percent == Decimal("12.5000")
    assert facts.available_quote_reserves_raw == 60


@pytest.mark.asyncio
async def test_collector_retries_rate_limit_without_bypassing_risk_evidence() -> None:
    rpc = RateLimitedRpc()
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    collector = SolanaRiskCollector(
        rpc,  # type: ignore[arg-type]
        commitment="confirmed",
        retry_count=3,
        retry_delay_seconds=0.4,
        sleep=sleep,
    )

    facts = await collector.collect(_context())

    assert rpc.largest_attempts == 3
    assert delays == [0.4, 0.8]
    assert facts.holder_error is None
    assert facts.top1_holder_percent == Decimal("62.5000")


def test_rules_emit_hard_reject_with_reasons_and_evidence() -> None:
    facts = OnChainRiskFacts(
        observed_at=NOW,
        source_slot=100,
        mint_state=MintAccountState(
            mint_authority=None, supply=1000, decimals=6, initialized=True, freeze_authority=CREATOR
        ),
        mint_error=None,
        top1_holder_percent=Decimal("45"),
        top5_holder_percent=Decimal("70"),
        top10_holder_percent=Decimal("85"),
        holder_error=None,
        circulating_supply_raw=900,
        creator_holding_percent=Decimal("10"),
        creator_holding_error=None,
        available_quote_reserves_raw=100,
        liquidity_error=None,
        excluded_market_token_accounts=1,
    )

    result = RiskAssessor(_policy()).assess(_context(), facts)

    assert result.allowed is False
    assert "freeze_authority_enabled" in result.hard_reject_reasons
    assert "top1_holder_above_limit" in result.hard_reject_reasons
    assert all(item.message for item in result.evidence)


def test_rules_keep_critical_missing_data_explicitly_unknown() -> None:
    facts = OnChainRiskFacts(
        observed_at=NOW,
        source_slot=None,
        mint_state=None,
        mint_error="rpc_429",
        top1_holder_percent=None,
        top5_holder_percent=None,
        top10_holder_percent=None,
        holder_error="rpc_429",
        circulating_supply_raw=None,
        creator_holding_percent=None,
        creator_holding_error="rpc_429",
        available_quote_reserves_raw=None,
        liquidity_error="rpc_429",
        excluded_market_token_accounts=0,
    )

    result = RiskAssessor(_policy()).assess(_context(), facts)

    assert result.allowed is None
    assert result.risk_score is None
    assert set(result.critical_unknowns) == {
        "mint_security",
        "holder_distribution",
        "creator_holding",
        "liquidity",
    }
    assert any(item.code == "mint_security" and item.value is None for item in result.evidence)


def test_rules_accept_independent_rpc_market_validation_for_third_party_stream() -> None:
    context = _context()
    context = replace(
        context,
        validation_state=MarketValidationState.INSUFFICIENT_DATA,
    )
    facts = OnChainRiskFacts(
        observed_at=NOW,
        source_slot=100,
        mint_state=MintAccountState(
            mint_authority=None,
            supply=1000,
            decimals=6,
            initialized=True,
            freeze_authority=None,
        ),
        mint_error=None,
        top1_holder_percent=Decimal("10"),
        top5_holder_percent=Decimal("20"),
        top10_holder_percent=Decimal("30"),
        holder_error=None,
        circulating_supply_raw=900,
        creator_holding_percent=Decimal("1"),
        creator_holding_error=None,
        available_quote_reserves_raw=100,
        liquidity_error=None,
        excluded_market_token_accounts=1,
    )

    result = RiskAssessor(_policy()).assess(context, facts)

    assert "market_validation" not in result.critical_unknowns
    evidence = next(item for item in result.evidence if item.code == "market_validation_state")
    assert evidence.value == MarketValidationState.VERIFIED_MARKET_DATA.value
