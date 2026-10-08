"""Integer reserve normalization and conservative, event-driven continuity tracking.

HEALTHY describes a validated snapshot, never a promise that logs cover direct vault
transfers. Execution must refresh accounts; an event-only state is INCOMPLETE.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from memebot.providers.solana.pump_idl import PumpSwapTrade, PumpTrade


class ReserveSemantics(StrEnum):
    PRE_TRADE = "PRE_TRADE"
    POST_TRADE = "POST_TRADE"
    RECONSTRUCTED_POST_TRADE = "RECONSTRUCTED_POST_TRADE"
    UNKNOWN = "UNKNOWN"


class StateStatus(StrEnum):
    BOOTSTRAPPING = "BOOTSTRAPPING"
    HEALTHY = "HEALTHY"
    DIVERGED = "DIVERGED"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class InvalidationScope(StrEnum):
    MARKET = "MARKET"
    POOL = "POOL"
    VENUE = "VENUE"
    GLOBAL = "GLOBAL"


class InvalidationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    reason: str
    scope: InvalidationScope
    program: str | None = None
    signature: str | None = None
    slot: int | None = None
    transaction_index: int | None = None
    instruction_index: int | None = None
    affected_markets: tuple[str, ...] = ()
    identity_known: bool = False
    reconciliation_queued: bool = False
    dimensions: tuple[str, ...] = ("reserves",)
    scope_reason: str = "explicit_market"
    detail: str | None = None


class NormalizedMarketState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    market: str | None = None
    state_source: str = "unknown"
    reserve_semantics: ReserveSemantics = ReserveSemantics.UNKNOWN
    state_quality: StateStatus = StateStatus.UNKNOWN
    state_slot: int | None = None
    last_signature: str | None = None
    last_event_ordinal: int | None = None
    quote_reserve: int | None = None
    token_reserve: int | None = None
    virtual_quote: int | None = None
    virtual_token: int | None = None
    virtual_offset: int | None = None
    raw_pre_quote: int | None = None
    raw_pre_token: int | None = None
    quote_vault_transfer: int | None = None
    reconciled_at: datetime | None = None
    events_since_reconciliation: int = 0
    continuity_status: str = "UNKNOWN"
    delta: dict[str, int] = {}
    reason: str | None = None
    identity_verified: bool = False
    program: str | None = None
    base_mint: str | None = None
    is_mayhem_mode: bool | None = None
    multi_event_ambiguous: bool = False
    execution_identity_verified: bool = False
    execution_config_verified: bool = False
    execution_assumptions_verified: bool = False
    invalidation_scope: str | None = None
    invalidation_reason: str | None = None

    @property
    def observational_price(self) -> Decimal | None:
        if self.continuity_status not in {"FIRST_OBSERVATION", "EXACT", "RPC_VALIDATED"}:
            return None
        if self.reserve_semantics == ReserveSemantics.UNKNOWN:
            return None
        token = self.virtual_token if self.virtual_token is not None else self.token_reserve
        quote = self.virtual_quote
        if quote is None and self.quote_reserve is not None:
            quote = self.quote_reserve + (self.virtual_offset or 0)
        return Decimal(quote) / Decimal(token) if token and quote and quote > 0 else None

    def evidence(self) -> dict[str, object]:
        from memebot.eligibility import UNIVERSE, entry_rejection

        result: dict[str, object] = {
            "state_source": self.state_source,
            "program": self.program,
            "is_mayhem_mode": self.is_mayhem_mode,
            "multi_event_ambiguous": self.multi_event_ambiguous,
            "state_semantics": self.reserve_semantics.value,
            "state_quality": self.state_quality.value,
            "state_slot": self.state_slot,
            "reconciled_at": self.reconciled_at,
            "continuity_status": self.continuity_status,
            "state_reason": self.reason,
            "identity_verified": self.identity_verified,
            "observational_trust": "OBSERVATIONAL_HEALTHY"
            if self.observational_price is not None
            else "OBSERVATIONAL_INCOMPLETE",
            "execution_identity_verified": self.execution_identity_verified,
            "execution_config_verified": self.execution_config_verified,
            "execution_assumptions_verified": self.execution_assumptions_verified,
            "invalidation_scope": self.invalidation_scope,
            "invalidation_reason": self.invalidation_reason,
        }
        reason = entry_rejection(result)
        result.update(
            trading_universe=UNIVERSE,
            entry_eligibility_status="ENTRY_READY" if reason is None else "REJECTED",
            entry_rejection_reason=reason,
        )
        return result

    def time_since_reconciliation_ms(self, now: datetime) -> int | None:
        if self.reconciled_at is None:
            return None
        return int((now - self.reconciled_at).total_seconds() * 1000)


def normalize_trade(
    event: PumpTrade | PumpSwapTrade,
    *,
    market: str,
    slot: int | None,
    signature: str,
    ordinal: int,
    multi_event_unknown: bool = False,
) -> NormalizedMarketState:
    from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID, PumpTrade

    common = dict(
        market=market,
        state_source="native_event",
        multi_event_ambiguous=multi_event_unknown,
        state_slot=slot,
        last_signature=signature,
        last_event_ordinal=ordinal,
        state_quality=StateStatus.INCOMPLETE,
        continuity_status="FIRST_OBSERVATION",
        reason="trade_only_coverage_requires_rpc",
        program=PUMP_PROGRAM_ID if isinstance(event, PumpTrade) else PUMP_AMM_PROGRAM_ID,
        base_mint=event.mint if isinstance(event, PumpTrade) else None,
        is_mayhem_mode=event.is_mayhem_mode if isinstance(event, PumpTrade) else None,
    )
    if isinstance(event, PumpTrade):
        if multi_event_unknown:
            return NormalizedMarketState(
                **{
                    **common,
                    "state_quality": StateStatus.UNKNOWN,
                    "continuity_status": "UNKNOWN",
                    "reason": "multi_event_order_unproven",
                },
            )
        return NormalizedMarketState(
            **common,
            reserve_semantics=ReserveSemantics.POST_TRADE,
            quote_reserve=event.real_quote_reserves,
            token_reserve=event.real_token_reserves,
            virtual_quote=event.virtual_quote_reserves,
            virtual_token=event.virtual_token_reserves,
        )
    transfer = event.quote_vault_transfer
    token = event.pool_base_token_reserves + (
        -event.base_amount if event.is_buy else event.base_amount
    )
    quote = (
        None
        if transfer is None
        else event.pool_quote_token_reserves + (transfer if event.is_buy else -transfer)
    )
    valid = transfer is not None and token > 0 and quote is not None and quote >= 0
    return NormalizedMarketState(
        **{
            **common,
            **(
                {}
                if valid
                else {
                    "state_quality": StateStatus.UNKNOWN,
                    "continuity_status": "UNKNOWN",
                    "reason": "actual_vault_transfer_missing_or_invalid",
                }
            ),
        },
        reserve_semantics=ReserveSemantics.RECONSTRUCTED_POST_TRADE
        if valid
        else ReserveSemantics.UNKNOWN,
        quote_reserve=quote if valid else None,
        token_reserve=token if valid else None,
        virtual_offset=event.virtual_quote_reserves,
        raw_pre_quote=event.pool_quote_token_reserves,
        raw_pre_token=event.pool_base_token_reserves,
        quote_vault_transfer=transfer,
    )


@dataclass(frozen=True)
class MarketIdentity:
    venue: str
    program: str
    market: str
    base_mint: str
    quote_mint: str
    base_vault: str | None
    quote_vault: str | None
    curve: str | None
    migrated: bool
    virtual_quote_offset: int
    virtual_token_offset: int
    config_version: str | None
    # Full bootstrap includes canonical address derivation, not just mint matching.
    canonical_verified: bool = False
    config_verified: bool = False
    execution_assumptions_verified: bool = False
    creator: str | None = None
    token_program: str | None = None
    source_curve: str | None = None
    config_references: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return (
            self.canonical_verified
            and self.config_verified
            and self.config_version is not None
            and self.execution_assumptions_verified
        )


@dataclass(frozen=True)
class ReconciliationPolicy:
    periodic_seconds: float | None = None
    event_count: int | None = None

    def due(self, state: NormalizedMarketState, now: datetime, duty: str) -> bool:
        if duty in {"bootstrap", "pre_entry", "open_position", "exit"}:
            return True
        if duty == "divergence":
            return state.state_quality in {
                StateStatus.DIVERGED,
                StateStatus.UNKNOWN,
                StateStatus.INCOMPLETE,
            }
        if duty == "event_count":
            return (
                self.event_count is not None
                and state.events_since_reconciliation >= self.event_count
            )
        return (
            duty == "periodic"
            and self.periodic_seconds is not None
            and (
                state.reconciled_at is None
                or (now - state.reconciled_at).total_seconds() >= self.periodic_seconds
            )
        )


class MarketStateTracker:
    def __init__(self, capacity: int = 10000) -> None:
        self.states: dict[str, NormalizedMarketState] = {}
        self.identities: dict[str, MarketIdentity] = {}
        self.capacity = capacity
        self.reconciliation_requests: dict[str, str] = {}
        self.invalidations: deque[InvalidationRecord] = deque(maxlen=capacity)
        self.config_generation: dict[str, int] = {}
        self.invalidation_revisions: dict[str, int] = {}
        # Signature of the latest reserve invalidation per market, so a trade event
        # never re-anchors on a transaction that itself carried the uncertainty.
        self.invalidation_signatures: dict[str, str | None] = {}

    def invalidate(
        self,
        market: str | None,
        reason: str,
        *,
        scope: InvalidationScope | None = None,
        program: str | None = None,
        signature: str | None = None,
        slot: int | None = None,
        transaction_index: int | None = None,
        instruction_index: int | None = None,
        affected_markets: set[str] | None = None,
        dimensions: tuple[str, ...] = ("reserves", "identity", "config"),
        scope_reason: str = "explicit_market",
    ) -> InvalidationRecord:
        detail = reason
        if not reason.isupper():
            if "migration" in reason or "graduation" in reason:
                reason = "MIGRATION"
            elif "config" in reason:
                reason = "CONFIG_CHANGE"
            elif any(
                word in reason
                for word in ("identity", "owner", "authority", "pda", "mint", "address")
            ):
                reason = "IDENTITY_MISMATCH"
            elif "vault" in reason:
                reason = "DIRECT_VAULT_CHANGE"
            elif "disconnect" in reason:
                reason = "STREAM_DISCONNECT"
            elif "truncat" in reason:
                reason = "TRUNCATED_LOG"
            elif "unsupported" in reason:
                reason = "UNKNOWN_NATIVE_INSTRUCTION"
            else:
                reason = "RPC_RECONCILIATION_FAILURE"
        actual_scope = scope or (
            InvalidationScope.MARKET
            if market
            else InvalidationScope.VENUE
            if program
            else InvalidationScope.GLOBAL
        )
        if affected_markets is not None:
            keys = sorted(affected_markets)
        elif market is not None:
            keys = [market]
        else:
            keys = [
                key
                for key, state in self.states.items()
                if program is None
                or state.program == program
                or (
                    self.identities.get(key) is not None and self.identities[key].program == program
                )
            ]
        identity_known = any(key in self.identities for key in keys)
        queued = False
        for key in keys:
            previous = self.states.get(key)
            if (
                previous is not None
                and slot is not None
                and previous.state_slot is not None
                and slot < previous.state_slot
            ):
                # A delayed notification cannot invalidate a newer atomic bank
                # or executed observation. Gaps without a slot still invalidate.
                continue
            if previous is not None and dimensions:
                self.invalidation_revisions[key] = self.invalidation_revisions.get(key, 0) + 1
            if "reserves" in dimensions:
                self.invalidation_signatures.pop(key, None)
                self.invalidation_signatures[key] = signature
                if len(self.invalidation_signatures) > self.capacity:
                    self.invalidation_signatures.pop(next(iter(self.invalidation_signatures)))
            if previous is not None:
                updates: dict[str, object] = (
                    {"invalidation_scope": actual_scope.value, "invalidation_reason": reason}
                    if dimensions
                    else {}
                )
                if "reserves" in dimensions:
                    updates.update(
                        state_quality=StateStatus.INCOMPLETE,
                        continuity_status="UNKNOWN",
                        reason=reason,
                    )
                if "identity" in dimensions:
                    updates.update(
                        identity_verified=False,
                        execution_identity_verified=False,
                        execution_assumptions_verified=False,
                    )
                if "config" in dimensions:
                    updates.update(
                        identity_verified=False,
                        execution_config_verified=False,
                        execution_assumptions_verified=False,
                        state_quality=StateStatus.INCOMPLETE,
                    )
                # Repeated shared-stream invalidations often target states that
                # are already invalid. Retain every evidence record/generation,
                # but avoid cloning thousands of unchanged Pydantic states.
                if any(getattr(previous, name) != value for name, value in updates.items()):
                    self.states[key] = previous.model_copy(update=updates)
            if "identity" in dimensions:
                self.identities.pop(key, None)
            elif "config" in dimensions and key in self.identities:
                self.identities[key] = replace(
                    self.identities[key], config_verified=False, config_version=None
                )
            if dimensions and len(self.reconciliation_requests) < self.capacity:
                self.reconciliation_requests[key] = reason
                queued = True
        if "config" in dimensions and actual_scope in {
            InvalidationScope.VENUE,
            InvalidationScope.GLOBAL,
        }:
            programs = (
                {program} if program else {s.program for s in self.states.values() if s.program}
            )
            for item in programs:
                if item is not None:
                    self.config_generation[item] = self.config_generation.get(item, 0) + 1
        record = InvalidationRecord(
            reason=reason,
            scope=actual_scope,
            program=program,
            signature=signature,
            slot=slot,
            transaction_index=transaction_index,
            instruction_index=instruction_index,
            affected_markets=tuple(keys),
            identity_known=identity_known,
            reconciliation_queued=queued,
            dimensions=dimensions,
            scope_reason=scope_reason,
            detail=detail if detail != reason else None,
        )
        self.invalidations.append(record)
        return record

    def observe(
        self,
        event: PumpTrade | PumpSwapTrade,
        *,
        market: str,
        slot: int | None,
        signature: str,
        ordinal: int,
        multi_event_unknown: bool = False,
    ) -> NormalizedMarketState:
        from memebot.providers.solana.pump_idl import PumpSwapTrade

        # Typed public normalization arguments keep providers and replay on the same path.
        state = normalize_trade(
            event,
            market=market,
            slot=slot,
            signature=signature,
            ordinal=ordinal,
            multi_event_unknown=multi_event_unknown,
        )
        assert state.market is not None
        previous = self.states.get(state.market)
        if previous is not None:
            if (
                state.last_signature == previous.last_signature
                and state.last_event_ordinal == previous.last_event_ordinal
            ):
                return previous
            if state.state_slot is None or (
                previous.state_slot is not None and state.state_slot < previous.state_slot
            ):
                # Reject the observation without overwriting the known state.
                return state.model_copy(
                    update={
                        "state_quality": StateStatus.UNKNOWN,
                        "continuity_status": "SLOT_REGRESSION",
                        "reason": "older_or_missing_slot",
                    }
                )
            if (
                not isinstance(event, PumpSwapTrade)
                and not multi_event_unknown
                and previous.observational_price is None
                and self.invalidation_signatures.get(state.market) != signature
            ):
                # A single Pump TradeEvent carries the program's exact post-trade
                # reserves, so observation re-anchors on it. Integer continuity is
                # checked again from here; execution still requires an RPC refresh.
                self.states[state.market] = state.model_copy(
                    update={
                        "reason": "reanchored_on_native_trade_event",
                        "events_since_reconciliation": previous.events_since_reconciliation + 1,
                        "reconciled_at": previous.reconciled_at,
                    }
                )
                return self.states[state.market]
            delta: dict[str, int] = {}
            if isinstance(event, PumpSwapTrade):
                pairs = [
                    ("quote", state.raw_pre_quote, previous.quote_reserve),
                    ("token", state.raw_pre_token, previous.token_reserve),
                    ("offset", state.virtual_offset, previous.virtual_offset),
                ]
            else:
                direction = 1 if event.is_buy else -1
                pairs = [
                    (
                        "quote",
                        state.quote_reserve,
                        None
                        if previous.quote_reserve is None
                        else previous.quote_reserve + direction * event.quote_amount,
                    ),
                    (
                        "token",
                        state.token_reserve,
                        None
                        if previous.token_reserve is None
                        else previous.token_reserve - direction * event.token_amount,
                    ),
                    (
                        "virtual_quote",
                        state.virtual_quote,
                        None
                        if previous.virtual_quote is None
                        else previous.virtual_quote + direction * event.quote_amount,
                    ),
                    (
                        "virtual_token",
                        state.virtual_token,
                        None
                        if previous.virtual_token is None
                        else previous.virtual_token - direction * event.token_amount,
                    ),
                ]
            known = all(
                current is not None and expected is not None for _, current, expected in pairs
            )
            for name, current, expected in pairs:
                if current is not None and expected is not None and current != expected:
                    delta[name] = current - expected
            invalid = previous.continuity_status not in {
                "FIRST_OBSERVATION",
                "EXACT",
                "RPC_VALIDATED",
            }
            state = state.model_copy(
                update={
                    "state_quality": StateStatus.DIVERGED if delta else StateStatus.INCOMPLETE,
                    "continuity_status": "DIVERGED"
                    if delta
                    else "UNKNOWN"
                    if not known or invalid
                    else "EXACT",
                    "delta": delta,
                    "reason": "integer_continuity_break"
                    if delta
                    else "reconciliation_required"
                    if invalid
                    else state.reason,
                    "events_since_reconciliation": previous.events_since_reconciliation + 1,
                    "reconciled_at": previous.reconciled_at,
                    "execution_identity_verified": previous.execution_identity_verified,
                    "execution_config_verified": previous.execution_config_verified,
                    "execution_assumptions_verified": previous.execution_assumptions_verified,
                    "invalidation_scope": previous.invalidation_scope if invalid else None,
                    "invalidation_reason": previous.invalidation_reason if invalid else None,
                }
            )
        if len(self.states) >= self.capacity and state.market not in self.states:
            victim = next(iter(self.states))
            self.states.pop(victim)
            self.invalidation_revisions.pop(victim, None)
            self.identities.pop(victim, None)
            self.reconciliation_requests.pop(victim, None)
        assert state.market is not None
        self.states[state.market] = state
        if state.continuity_status in {"DIVERGED", "UNKNOWN"} and (
            state.delta or multi_event_unknown or state.invalidation_scope is None
        ):
            cause = (
                "CONTINUITY_BREAK"
                if state.delta
                else "MULTI_EVENT_AMBIGUITY"
                if multi_event_unknown
                else "UNKNOWN_HISTORY"
            )
            self.invalidate(
                state.market,
                cause,
                program=state.program,
                signature=signature,
                slot=slot,
                dimensions=(),
            )
            # Keep the precise DIVERGED result, not a generic UNKNOWN overwrite.
            self.states[state.market] = state.model_copy(
                update={
                    "invalidation_scope": "MARKET",
                    "invalidation_reason": cause,
                }
            )
            self.reconciliation_requests[state.market] = state.reason or "unknown_history"
            self.invalidations[-1] = self.invalidations[-1].model_copy(
                update={"reconciliation_queued": True}
            )
        return self.states[state.market]

    def apply_mayhem_update(
        self, event: object, *, market: str, signature: str, slot: int, ordinal: int
    ) -> NormalizedMarketState:
        from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpMayhemUpdate

        if not isinstance(event, PumpMayhemUpdate):
            raise TypeError("expected typed Mayhem mutation")
        previous = self.states.get(market)
        delta: dict[str, int] = {}
        if previous is not None:
            if previous.state_slot is not None and slot < previous.state_slot:
                return previous
            for key, actual in (
                ("virtual_quote", event.virtual_quote_reserves),
                ("virtual_token", event.virtual_token_reserves),
                ("quote_reserve", event.real_quote_reserves),
                ("token_reserve", event.real_token_reserves),
            ):
                expected = getattr(previous, key)
                if expected is not None and actual != expected:
                    delta[key] = actual - expected
        state = NormalizedMarketState(
            market=market,
            program=PUMP_PROGRAM_ID,
            base_mint=event.mint,
            state_source="native_mutation",
            reserve_semantics=ReserveSemantics.POST_TRADE,
            state_quality=StateStatus.DIVERGED if delta else StateStatus.INCOMPLETE,
            state_slot=slot,
            last_signature=signature,
            last_event_ordinal=ordinal,
            quote_reserve=event.real_quote_reserves,
            token_reserve=event.real_token_reserves,
            virtual_quote=event.new_virtual_quote_reserves,
            virtual_token=event.new_virtual_token_reserves,
            continuity_status="DIVERGED"
            if delta
            else "FIRST_OBSERVATION"
            if previous is None
            else "EXACT"
            if previous.observational_price is not None
            else "UNKNOWN",
            delta=delta,
            is_mayhem_mode=True,
            reason="MAYHEM_MUTATION",
        )
        self.states[market] = state
        if delta:
            self.invalidate(
                market,
                "CONTINUITY_BREAK",
                program=PUMP_PROGRAM_ID,
                signature=signature,
                slot=slot,
                dimensions=("reserves",),
            )
            self.states[market] = state
        return state

    def pending_reconciliation_markets(self, eligible: set[str], *, limit: int) -> list[str]:
        """Coalesce repairs; caller admits open exposure/candidates within its RPC budget."""
        if limit < 0:
            raise ValueError("negative reconciliation budget")
        return [market for market in self.reconciliation_requests if market in eligible][:limit]

    def reconcile(
        self,
        identity: MarketIdentity,
        snapshot: NormalizedMarketState,
        *,
        validated: bool,
        now: datetime,
    ) -> bool:
        previous = self.states.get(identity.market)
        cached = self.identities.get(identity.market)
        if (
            previous is not None
            and previous.state_slot is not None
            and snapshot.state_slot is not None
            and snapshot.state_slot < previous.state_slot
        ):
            self.invalidate(
                identity.market,
                "RPC_SLOT_REGRESSION",
                program=identity.program,
                dimensions=(),
                slot=snapshot.state_slot,
            )
            self.reconciliation_requests[identity.market] = "RPC_SLOT_REGRESSION"
            self.invalidations[-1] = self.invalidations[-1].model_copy(
                update={"reconciliation_queued": True}
            )
            return False
        if cached is not None and cached != identity:
            self.invalidate(identity.market, "identity_or_config_changed")
            return False
        if (
            not validated
            or snapshot.market != identity.market
            or snapshot.state_slot is None
            or snapshot.token_reserve is None
            or snapshot.quote_reserve is None
            or snapshot.token_reserve <= 0
            or snapshot.quote_reserve < 0
            or (
                previous is not None
                and previous.state_slot is not None
                and snapshot.state_slot < previous.state_slot
            )
        ):
            self.invalidate(identity.market, "rpc_identity_slot_or_decode_invalid")
            return False
        self.identities[identity.market] = identity
        self.reconciliation_requests.pop(identity.market, None)
        self.states[identity.market] = snapshot.model_copy(
            update={
                "state_source": "validated_rpc",
                "state_quality": StateStatus.HEALTHY
                if identity.complete
                else StateStatus.INCOMPLETE,
                "continuity_status": "RPC_VALIDATED",
                "reconciled_at": now,
                "events_since_reconciliation": 0,
                "identity_verified": identity.complete,
                "execution_identity_verified": identity.canonical_verified,
                "execution_config_verified": identity.config_verified,
                "execution_assumptions_verified": identity.execution_assumptions_verified,
                "program": identity.program,
                "base_mint": identity.base_mint,
                "reason": None if identity.complete else "canonical_or_config_bootstrap_incomplete",
            }
        )
        return True
