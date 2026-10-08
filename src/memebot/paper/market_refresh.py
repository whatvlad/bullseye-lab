from __future__ import annotations

import asyncio
import base64
import binascii
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from time import monotonic
from typing import Protocol

from memebot.core.clock import utc_now
from memebot.market_state import (
    MarketIdentity,
    MarketStateTracker,
    NormalizedMarketState,
    ReserveSemantics,
    StateStatus,
)
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.providers.pool_lookup import PoolLookup
from memebot.providers.solana.base import Commitment, SolanaRpcProvider
from memebot.providers.solana.bootstrap import ReadOnlyConfigCache, bootstrap_curve, bootstrap_pool
from memebot.providers.solana.canonical import curve_address, pool_address
from memebot.providers.solana.encoding import BorshDecodeError
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    decode_bonding_curve_account,
    decode_pool_account,
    decode_token_account,
)
from memebot.providers.solana.rpc import SolanaRpcError

from .models import ExecutionMarketSnapshot
from .price_safety import source_disagreement

_MIN_SLOT_RETRY_SECONDS = 0.2
_MIN_SLOT_RETRY_BUDGET_SECONDS = 2.0


class CurrentPaperMarketRefresher:
    """One atomic canonical account/config bank; no historical proof authorization."""

    def __init__(
        self,
        rpc: object,
        *,
        max_read_seconds: float = 5,
        for_exit: bool = False,
        state_tracker: MarketStateTracker | None = None,
    ) -> None:
        from typing import cast

        from .candidate_proof import CandidateProofService, ReadRpc

        self.reader = CandidateProofService(cast(ReadRpc, rpc))
        self.max_read_seconds = max_read_seconds
        self.for_exit = for_exit
        self.state_tracker = state_tracker

    async def refresh(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot:
        from memebot.eligibility import paper_candidate_rejection

        from .candidate_proof import ProofFailure

        revision = (
            self.state_tracker.invalidation_revisions.get(market.market, 0)
            if self.state_tracker is not None
            else None
        )

        evidence = market.normalized_state.evidence() if market.normalized_state else {}
        reason = paper_candidate_rejection(
            evidence,
            venue=market.venue.value,
            lifecycle=market.lifecycle.value,
            complete=market.curve_complete,
        )
        if reason == "STATE_UNKNOWN" and market.venue == LaunchVenue.PUMP_FUN:
            # Missing observational identity does not forbid verifying current identity.
            # This read grants no fill; the atomic decoder below rejects unknown mode/config.
            reason = None
        if self.for_exit:
            # Observational entry exclusions cannot prevent verification of existing exposure.
            reason = None
            if market.venue == LaunchVenue.PUMP_SWAP or market.curve_complete:
                return await self._migration_exit(market)
        if reason or market.market != curve_address(market.mint):
            return replace(
                market,
                rpc_state="degraded",
                execution_state=None,
                data_quality=reason or "canonical_curve_pda_mismatch",
            )
        try:
            started = monotonic()
            while True:
                try:
                    bundle = await self.reader._bundle(
                        None, mint=market.mint, minimum_slot=market.source_slot or 0
                    )
                    break
                except SolanaRpcError as error:
                    # -32016: the RPC node is still behind the stream's slot. It
                    # normally catches up within a few hundred milliseconds.
                    if (
                        error.code != "rpc_-32016"
                        or monotonic() - started + _MIN_SLOT_RETRY_SECONDS
                        > _MIN_SLOT_RETRY_BUDGET_SECONDS
                    ):
                        raise
                    await asyncio.sleep(_MIN_SLOT_RETRY_SECONDS)
            if monotonic() - started > self.max_read_seconds:
                return replace(
                    market,
                    rpc_state="degraded",
                    execution_state=None,
                    data_quality="current_atomic_read_too_slow",
                )
        except ProofFailure as error:
            if self.for_exit and str(error) == "excluded mode or completion":
                return await self._migration_exit(market)
            return replace(
                market,
                rpc_state="degraded",
                execution_state=None,
                data_quality=f"current_atomic_{error.status}:{error}",
            )
        except (SolanaRpcError, TimeoutError, OSError):
            return replace(
                market,
                rpc_state="degraded",
                execution_state=None,
                data_quality="current_atomic_refresh_failed",
            )
        curve = bundle["curve"]
        if any(curve[k] <= 0 for k in ("virtual_token_reserves", "virtual_quote_reserves")) or any(
            curve[k] < 0 for k in ("real_token_reserves", "real_quote_reserves")
        ):
            return replace(
                market,
                rpc_state="degraded",
                execution_state=None,
                data_quality="malformed_reserves",
            )
        at = datetime.fromisoformat(bundle["account_batch"]["received_at"])
        state = NormalizedMarketState(
            market=market.market,
            program=PUMP_PROGRAM_ID,
            base_mint=market.mint,
            state_source="atomic_current_paper",
            reserve_semantics=ReserveSemantics.POST_TRADE,
            state_quality=StateStatus.HEALTHY,
            state_slot=bundle["slot"],
            reconciled_at=at,
            quote_reserve=curve["real_quote_reserves"],
            token_reserve=curve["real_token_reserves"],
            virtual_quote=curve["virtual_quote_reserves"],
            virtual_token=curve["virtual_token_reserves"],
            continuity_status="RPC_VALIDATED",
            identity_verified=True,
            is_mayhem_mode=False,
            execution_identity_verified=True,
            execution_config_verified=True,
            execution_assumptions_verified=True,
        )
        if self.state_tracker is not None and (
            revision == self.state_tracker.invalidation_revisions.get(market.market, 0)
        ):
            binding = bundle["binding"]
            identity = MarketIdentity(
                venue="pump_fun",
                program=PUMP_PROGRAM_ID,
                market=market.market,
                base_mint=market.mint,
                quote_mint=binding["quote"],
                base_vault=binding["vault"],
                quote_vault=None,
                curve=binding["curve"],
                migrated=False,
                virtual_quote_offset=0,
                virtual_token_offset=0,
                config_version=binding["config_version"],
                canonical_verified=True,
                config_verified=True,
                execution_assumptions_verified=True,
                creator=binding["creator"],
                token_program=binding["token_program"],
                config_references=tuple(binding["config_addresses"]),
            )
            # Reuse the existing atomic risk bank, never an extra RPC read.
            # reconcile rejects slot regression; an in-flight invalidation
            # prevents publication. This starts a new observational anchor,
            # and does not repair past rolling samples or authorize a fill.
            current = self.state_tracker.states.get(market.market)
            healthy_history = (
                current is not None
                and current.observational_price is not None
                and current.execution_identity_verified
                and current.execution_config_verified
                and current.execution_assumptions_verified
                and self.state_tracker.identities.get(market.market) == identity
            )
            if not healthy_history:
                self.state_tracker.reconcile(identity, state, validated=True, now=at)
            # A routine risk refresh must not repeatedly move a healthy event
            # history ahead to the RPC bank, rejecting the intervening trades.
            # Execution still uses the fresh atomic bank returned below.
        price = Decimal(curve["virtual_quote_reserves"]) / Decimal(curve["virtual_token_reserves"])
        return replace(
            market,
            observed_at=at,
            received_timestamp=at,
            source_timestamp=None,
            source_slot=bundle["slot"],
            observed_price_raw=price,
            price_source="atomic_current_paper",
            rpc_state="healthy",
            data_quality="canonical_atomic_bank_verified",
            normalized_state=state,
            execution_state=bundle,
            is_mayhem_mode=False,
            real_token_reserves_raw=curve["real_token_reserves"],
            real_quote_reserves_raw=curve["real_quote_reserves"],
            virtual_token_reserves_raw=curve["virtual_token_reserves"],
            virtual_quote_reserves_raw=curve["virtual_quote_reserves"],
            price_source_disagreement_pct=source_disagreement(market.feed_reference_price, price),
        )

    async def _migration_exit(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot:
        from .migration_exit import read_migration_exit

        try:
            started = monotonic()
            refreshed = await read_migration_exit(self.reader.rpc, market)
            if monotonic() - started > self.max_read_seconds:
                raise ValueError("migration_atomic_read_too_slow")
            return refreshed
        except (ValueError, KeyError, TypeError, SolanaRpcError, TimeoutError, OSError) as error:
            reason = str(error) if isinstance(error, ValueError) else type(error).__name__
            return replace(
                market,
                rpc_state="degraded",
                execution_state=None,
                data_quality=f"migration_exit_unavailable:{reason}",
            )


class MarketSnapshotRefresher(Protocol):
    async def refresh(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot: ...


@dataclass(frozen=True, slots=True)
class MarketRefreshResult:
    market: ExecutionMarketSnapshot
    status: str
    detail: str | None = None


class FallbackMarketSnapshotRefresher:
    """Try a dedicated low-volume exit RPC when the primary service is unavailable."""

    def __init__(self, *refreshers: MarketSnapshotRefresher) -> None:
        self._refreshers = refreshers

    async def refresh(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot:
        current = market
        failures = []
        for refresher in self._refreshers:
            try:
                refreshed = await refresher.refresh(current)
            except (SolanaRpcError, TimeoutError, OSError):
                failures.append("rpc_transport_error")
                continue
            failures.append(refreshed.data_quality or "rpc_unavailable")
            if refreshed.observed_at > current.observed_at and refreshed.rpc_state != "degraded":
                if current.curve_complete and refreshed.market == current.market:
                    return replace(
                        refreshed,
                        curve_complete=True,
                        rpc_state="degraded",
                        data_quality="curve_completion_disagreement",
                    )
                return refreshed
            if refreshed.curve_complete:
                current = replace(current, curve_complete=True)
        return replace(
            current,
            rpc_state="degraded",
            execution_state=None,
            data_quality="rpc_unavailable:" + "|".join(failures),
        )


class SolanaRpcMarketSnapshotRefresher:
    """Refresh execution reserves from account state without waiting for a new trade."""

    def __init__(
        self,
        rpc: SolanaRpcProvider,
        *,
        commitment: Commitment,
        pool_lookup: PoolLookup | None = None,
        on_recovered: Callable[[ExecutionMarketSnapshot], Awaitable[None]] | None = None,
        source_name: str = "rpc_reserves",
        state_tracker: MarketStateTracker | None = None,
        config_cache: ReadOnlyConfigCache | None = None,
        bootstrap_identity: bool = True,
    ) -> None:
        self._rpc = rpc
        self._commitment = commitment
        self._pool_lookup = pool_lookup
        self._on_recovered = on_recovered
        self._source_name = source_name
        self.state_tracker = state_tracker or MarketStateTracker()
        self.config_cache = config_cache or ReadOnlyConfigCache(rpc, commitment)
        self.bootstrap_identity = bootstrap_identity
        self.bootstrap_evidence: dict[str, object] = {}

    async def refresh(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot:
        result = await self.refresh_with_diagnostics(market)
        if result.status != "refreshed":
            identity_failure = any(
                word in (result.detail or "")
                for word in ("identity", "owner", "authority", "pda", "mint", "address", "binding")
            )
            self.state_tracker.invalidate(
                market.market,
                "IDENTITY_MISMATCH" if identity_failure else "RPC_RECONCILIATION_FAILURE",
                dimensions=("reserves", "identity", "config")
                if identity_failure
                else ("reserves",),
            )
            return replace(
                result.market, rpc_state="degraded", data_quality=result.detail or "rpc_error"
            )
        refreshed = result.market
        same_market = refreshed.market == market.market
        identity = self.state_tracker.identities.get(refreshed.market)
        state = NormalizedMarketState(
            market=refreshed.market,
            state_source="validated_rpc",
            reserve_semantics=ReserveSemantics.POST_TRADE,
            state_slot=refreshed.source_slot,
            quote_reserve=refreshed.real_quote_reserves_raw,
            token_reserve=refreshed.real_token_reserves_raw,
            virtual_quote=refreshed.virtual_quote_reserves_raw
            if refreshed.venue == LaunchVenue.PUMP_FUN
            else None,
            virtual_token=refreshed.virtual_token_reserves_raw,
            virtual_offset=refreshed.virtual_quote_reserves_raw
            if refreshed.venue == LaunchVenue.PUMP_SWAP
            else None,
            is_mayhem_mode=refreshed.is_mayhem_mode,
            multi_event_ambiguous=bool(
                market.normalized_state and market.normalized_state.multi_event_ambiguous
            ),
        )
        if identity is None or not self.state_tracker.reconcile(
            identity, state, validated=True, now=refreshed.observed_at
        ):
            return replace(
                market, rpc_state="degraded", data_quality="identity_reconciliation_failed"
            )
        reference = market.feed_reference_price if same_market else None
        return replace(
            refreshed,
            price_source=self._source_name,
            # RPC account slot is known; its wall-clock source timestamp is not.
            source_timestamp=None,
            received_timestamp=refreshed.observed_at,
            feed_timestamp=market.feed_timestamp,
            feed_reference_price=reference,
            price_source_disagreement_pct=source_disagreement(
                reference, refreshed.observed_price_raw
            ),
            data_quality="rpc_slot_known_source_time_unknown",
            rpc_state="healthy",
            normalized_state=self.state_tracker.states[refreshed.market],
        )

    async def refresh_with_diagnostics(
        self, market: ExecutionMarketSnapshot
    ) -> MarketRefreshResult:
        self.state_tracker.states.setdefault(
            market.market,
            NormalizedMarketState(
                market=market.market,
                state_quality=StateStatus.BOOTSTRAPPING,
                reason="rpc_bootstrap_pending",
            ),
        )
        try:
            account = await self._rpc.get_account(market.market, self._commitment)
            if account is None:
                return MarketRefreshResult(market, "not_refreshed", "market_account_not_found")
            if market.source_slot is not None and account.slot < market.source_slot:
                return MarketRefreshResult(market, "not_refreshed", "rpc_slot_regressed")
            if account.owner == PUMP_PROGRAM_ID:
                if self.bootstrap_identity and curve_address(market.mint) != account.address:
                    return MarketRefreshResult(
                        market, "not_refreshed", "canonical_curve_pda_mismatch"
                    )
                curve = decode_bonding_curve_account(_data(account.data_base64))
                if curve.complete:
                    if self._pool_lookup is not None:
                        for address in await self._pool_lookup.pools(market.mint):
                            pool_account = await self._rpc.get_account(address, self._commitment)
                            if pool_account is None or pool_account.owner != PUMP_AMM_PROGRAM_ID:
                                continue
                            candidate = replace(
                                market,
                                market=address,
                                source_slot=account.slot,
                                venue=LaunchVenue.PUMP_SWAP,
                                lifecycle=MarketLifecycle.POST_GRADUATION,
                                real_token_reserves_raw=None,
                                real_quote_reserves_raw=None,
                                virtual_token_reserves_raw=None,
                                virtual_quote_reserves_raw=None,
                                curve_complete=False,
                            )
                            resolved = await self.refresh_with_diagnostics(candidate)
                            if resolved.status == "refreshed":
                                if self._on_recovered is not None:
                                    await self._on_recovered(resolved.market)
                                return resolved
                    return MarketRefreshResult(
                        replace(
                            market,
                            curve_complete=True,
                            real_token_reserves_raw=curve.real_token_reserves,
                            real_quote_reserves_raw=curve.real_quote_reserves,
                            virtual_token_reserves_raw=curve.virtual_token_reserves,
                            virtual_quote_reserves_raw=curve.virtual_quote_reserves,
                        ),
                        "not_refreshed",
                        "completed_curve_pool_unavailable",
                    )
                if not _same_quote_asset(curve.quote_mint, market.quote_asset):
                    return MarketRefreshResult(
                        market,
                        "not_refreshed",
                        f"quote_mint_mismatch:{curve.quote_mint}:{market.quote_asset}",
                    )
                token_reserves = curve.virtual_token_reserves
                quote_reserves = curve.virtual_quote_reserves
                if token_reserves <= 0 or quote_reserves <= 0:
                    return MarketRefreshResult(market, "not_refreshed", "invalid_curve_reserves")
                cached_curve = self.state_tracker.identities.get(market.market)
                if self.bootstrap_identity:
                    await self.config_cache.ensure(self.state_tracker.config_generation)
                    version = self.config_cache.version("pump_fun")
                    if (
                        cached_curve is None
                        or not cached_curve.canonical_verified
                        or cached_curve.config_version != version
                    ):
                        proof = await bootstrap_curve(
                            self._rpc,
                            self._commitment,
                            mint=market.mint,
                            account=account,
                            curve=curve,
                            config_version=version,
                            standard_only=False,  # Existing exposure may need exit recovery.
                        )
                        self.bootstrap_evidence[market.market] = proof
                        if proof.identity is None:
                            return MarketRefreshResult(market, "not_refreshed", proof.error)
                        self.state_tracker.identities[market.market] = proof.identity
                    elif (
                        cached_curve.quote_mint != curve.quote_mint
                        or cached_curve.creator != curve.creator
                    ):
                        self.state_tracker.invalidate(
                            market.market,
                            "IDENTITY_MISMATCH",
                            program=account.owner,
                            slot=account.slot,
                        )
                        return MarketRefreshResult(
                            market, "not_refreshed", "curve_identity_rebootstrap_required"
                        )
                self.state_tracker.identities.setdefault(
                    market.market,
                    MarketIdentity(
                        "pump_fun",
                        account.owner,
                        market.market,
                        market.mint,
                        curve.quote_mint,
                        None,
                        None,
                        market.market,
                        curve.complete,
                        curve.virtual_quote_reserves - curve.real_quote_reserves,
                        curve.virtual_token_reserves - curve.real_token_reserves,
                        None,
                    ),
                )
                return MarketRefreshResult(
                    replace(
                        market,
                        observed_at=utc_now(),
                        venue=LaunchVenue.PUMP_FUN,
                        is_mayhem_mode=curve.is_mayhem_mode,
                        source_slot=account.slot,
                        observed_price_raw=Decimal(quote_reserves) / Decimal(token_reserves),
                        real_token_reserves_raw=curve.real_token_reserves,
                        real_quote_reserves_raw=curve.real_quote_reserves,
                        virtual_token_reserves_raw=token_reserves,
                        virtual_quote_reserves_raw=quote_reserves,
                        curve_complete=curve.complete,
                    ),
                    "refreshed",
                )
            if account.owner != PUMP_AMM_PROGRAM_ID:
                return MarketRefreshResult(
                    market, "not_refreshed", f"unsupported_market_owner:{account.owner}"
                )
            pool = decode_pool_account(_data(account.data_base64))
            if (
                self.bootstrap_identity
                and pool_address(pool.index, pool.creator, pool.base_mint, pool.quote_mint)
                != account.address
            ):
                return MarketRefreshResult(market, "not_refreshed", "canonical_pool_pda_mismatch")
            if pool.base_mint != market.mint or pool.quote_mint != market.quote_asset:
                return MarketRefreshResult(market, "not_refreshed", "pool_mint_mismatch")
            base_account, quote_account = await self._rpc.get_multiple_accounts(
                [pool.pool_base_token_account, pool.pool_quote_token_account],
                self._commitment,
            )
            if base_account is None or quote_account is None:
                return MarketRefreshResult(market, "not_refreshed", "pool_reserve_account_missing")
            token_programs = {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}
            if (
                base_account.owner not in token_programs
                or quote_account.owner not in token_programs
            ):
                return MarketRefreshResult(market, "not_refreshed", "unsupported_token_program")
            base = decode_token_account(_data(base_account.data_base64))
            quote = decode_token_account(_data(quote_account.data_base64))
            if base.mint != market.mint or quote.mint != market.quote_asset:
                return MarketRefreshResult(market, "not_refreshed", "pool_token_mint_mismatch")
            if base.owner != market.market or quote.owner != market.market:
                self.state_tracker.invalidate(market.market, "vault_authority_mismatch")
                return MarketRefreshResult(market, "not_refreshed", "vault_authority_mismatch")
            if (
                base_account.slot != quote_account.slot
                or min(base_account.slot, quote_account.slot) < account.slot
            ):
                return MarketRefreshResult(market, "not_refreshed", "vault_slot_incoherent")
            identity = MarketIdentity(
                "pump_swap",
                account.owner,
                market.market,
                pool.base_mint,
                pool.quote_mint,
                pool.pool_base_token_account,
                pool.pool_quote_token_account,
                None,
                pool.index == 0,
                pool.virtual_quote_reserves,
                0,
                None,
            )
            cached = self.state_tracker.identities.get(market.market)
            if self.bootstrap_identity:
                await self.config_cache.ensure(self.state_tracker.config_generation)
                version = self.config_cache.version("pump_swap")
                if (
                    cached is None
                    or not cached.canonical_verified
                    or cached.config_version != version
                ):
                    proof = await bootstrap_pool(
                        self._rpc,
                        self._commitment,
                        account=account,
                        pool=pool,
                        base_vault=base_account,
                        quote_vault=quote_account,
                        config_version=version,
                    )
                    self.bootstrap_evidence[market.market] = proof
                    if proof.identity is None:
                        return MarketRefreshResult(market, "not_refreshed", proof.error)
                    identity = proof.identity
                else:
                    identity = cached
                    if (
                        cached.base_vault != pool.pool_base_token_account
                        or cached.quote_vault != pool.pool_quote_token_account
                        or cached.base_mint != pool.base_mint
                        or cached.quote_mint != pool.quote_mint
                        or cached.creator != pool.coin_creator
                        or cached.virtual_quote_offset != pool.virtual_quote_reserves
                    ):
                        self.state_tracker.invalidate(
                            market.market,
                            "IDENTITY_MISMATCH",
                            program=account.owner,
                            slot=account.slot,
                        )
                        return MarketRefreshResult(
                            market, "not_refreshed", "pool_identity_rebootstrap_required"
                        )
            if not self.bootstrap_identity and cached is not None and cached != identity:
                self.state_tracker.invalidate(market.market, "pool_identity_or_offset_changed")
                return MarketRefreshResult(
                    market, "not_refreshed", "pool_identity_rebootstrap_required"
                )
            self.state_tracker.identities[market.market] = identity
            effective_quote = quote.amount + pool.virtual_quote_reserves
            if base.amount <= 0 or effective_quote <= 0:
                return MarketRefreshResult(market, "not_refreshed", "invalid_pool_reserves")
            return MarketRefreshResult(
                replace(
                    market,
                    venue=LaunchVenue.PUMP_SWAP,
                    lifecycle=MarketLifecycle.POST_GRADUATION,
                    curve_complete=False,
                    observed_at=utc_now(),
                    source_slot=max(account.slot, base_account.slot, quote_account.slot),
                    observed_price_raw=Decimal(effective_quote) / Decimal(base.amount),
                    real_token_reserves_raw=base.amount,
                    real_quote_reserves_raw=quote.amount,
                    virtual_token_reserves_raw=None,
                    virtual_quote_reserves_raw=pool.virtual_quote_reserves,
                ),
                "refreshed",
            )
        except (SolanaRpcError, BorshDecodeError, binascii.Error, ValueError) as error:
            detail = error.code if isinstance(error, SolanaRpcError) else type(error).__name__
            return MarketRefreshResult(market, "error", detail)


def _data(encoded: str) -> bytes:
    return base64.b64decode(encoded, validate=True)


def _same_quote_asset(onchain_mint: str, market_quote: str) -> bool:
    """Treat native SOL and wrapped SOL as the same economic quote asset."""
    sol_mints = {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}
    return onchain_mint == market_quote or {onchain_mint, market_quote} <= sol_mints
