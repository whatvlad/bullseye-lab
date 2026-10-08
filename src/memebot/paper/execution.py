from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal

from memebot.eligibility import entry_rejection
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue
from memebot.models.paper import (
    FillQuality,
    PaperExecutionEvidence,
    PaperFill,
    PaperOrderResult,
    PaperOrderSide,
    PaperOrderStatus,
    PositionEffect,
)
from memebot.providers.price.base import QuotePrice

from .fees import effective_venue_fee_bps, pump_market_cap_sol
from .models import ExecutionMarketSnapshot
from .price_safety import price_metadata
from .standard_math import buy_exact_input, sell_quote

_BPS = Decimal(10_000)
_LAMPORTS_PER_SOL = Decimal(1_000_000_000)


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    venue_fee_bps: Decimal
    latency_slippage_bps: Decimal
    network_fee_sol: Decimal
    priority_fee_sol: Decimal
    compute_latency_ms: int
    submission_latency_ms: int
    max_market_staleness_seconds: int
    max_quote_price_staleness_seconds: int
    execution_provider_fee_bps: Decimal = Decimal("50")
    additional_slippage_bps: Decimal = Decimal("50")
    adverse_fill_bps: Decimal = Decimal("50")
    require_atomic_pump_state: bool = False


class PaperFillSimulator:
    """Constant-product paper fills using only state available at decision time."""

    def __init__(self, policy: ExecutionPolicy) -> None:
        self._policy = policy

    def simulate_buy(
        self,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        *,
        requested_portfolio_amount: Decimal,
        signal_at: datetime,
        decision_at: datetime,
        executed_at: datetime | None = None,
    ) -> PaperOrderResult:
        if market.execution_state is not None:
            return self._simulate_current(
                market,
                quote_price,
                side=PaperOrderSide.BUY,
                requested=requested_portfolio_amount,
                tokens=None,
                effect=PositionEffect.OPEN,
                reason=None,
                signal_at=signal_at,
                decision_at=decision_at,
                executed_at=executed_at,
            )
        if self._policy.require_atomic_pump_state:
            return _rejected(
                PaperOrderSide.BUY,
                requested_portfolio_amount,
                "atomic_current_execution_state_required",
            )
        scope_block = entry_rejection(
            price_metadata(market, executed_at or decision_at),
            venue=market.venue.value,
            lifecycle=market.lifecycle.value,
            mayhem=market.is_mayhem_mode,
            complete=market.curve_complete,
        )
        if scope_block:
            return _rejected(PaperOrderSide.BUY, requested_portfolio_amount, scope_block)
        rejection = self._validate(market, quote_price, executed_at or decision_at)
        if rejection is not None:
            return _rejected(PaperOrderSide.BUY, requested_portfolio_amount, rejection)
        reserves = _reserves(market)
        if reserves is None:
            return _rejected(
                PaperOrderSide.BUY,
                requested_portfolio_amount,
                "reliable_market_reserves_unavailable",
            )
        quote_reserve, token_reserve = reserves
        gross_quote = requested_portfolio_amount / quote_price.price * _LAMPORTS_PER_SOL
        venue_fee_bps, fee_source = effective_venue_fee_bps(
            market, fallback_bps=self._policy.venue_fee_bps
        )
        venue_fee = gross_quote * venue_fee_bps / _BPS
        execution_provider_fee = gross_quote * self._policy.execution_provider_fee_bps / _BPS
        net_curve_input = gross_quote - venue_fee
        if market.venue == LaunchVenue.PUMP_FUN:
            # Official buyExactSolIn formula under the existing 95+30 bps assumption.
            # Fee-config/creator verification remains required for live execution.
            budget = gross_quote.to_integral_value(rounding=ROUND_DOWN)
            net_sol = (budget * _BPS / (_BPS + venue_fee_bps)).to_integral_value(
                rounding=ROUND_DOWN
            )
            venue_fee = sum(
                (
                    (net_sol * component / _BPS).to_integral_value(rounding=ROUND_CEILING)
                    for component in (Decimal(95), Decimal(30))
                ),
                Decimal(0),
            )
            net_sol -= max(Decimal(0), net_sol + venue_fee - budget)
            net_curve_input = net_sol - 1
        if net_curve_input <= 0:
            return _rejected(PaperOrderSide.BUY, requested_portfolio_amount, "fees_consume_order")
        token_out = Decimal(token_reserve) - (
            Decimal(quote_reserve)
            * Decimal(token_reserve)
            / (Decimal(quote_reserve) + net_curve_input)
        )
        if (
            market.real_token_reserves_raw is not None
            and token_out > market.real_token_reserves_raw
        ):
            return _rejected(
                PaperOrderSide.BUY, requested_portfolio_amount, "insufficient_real_token_reserves"
            )
        curve_price = net_curve_input / token_out
        executable_price = gross_quote / token_out
        token_out *= _BPS - self._policy.latency_slippage_bps
        token_out /= _BPS
        token_out = token_out.to_integral_value(rounding=ROUND_DOWN)
        if token_out <= 0:
            return _rejected(PaperOrderSide.BUY, requested_portfolio_amount, "non_positive_fill")
        fill = self._fill(
            side=PaperOrderSide.BUY,
            market=market,
            quote_price=quote_price,
            signal_at=signal_at,
            decision_at=decision_at,
            token_amount=token_out,
            gross_quote=gross_quote,
            venue_fee=venue_fee,
            execution_provider_fee=execution_provider_fee,
            requested_portfolio_amount=requested_portfolio_amount,
            venue_fee_bps=venue_fee_bps,
            fee_source=fee_source,
            executed_at=executed_at,
            curve_price=curve_price,
            executable_price=executable_price,
        )
        return PaperOrderResult(
            status=PaperOrderStatus.FILLED,
            side=PaperOrderSide.BUY,
            position_effect=PositionEffect.OPEN,
            requested_portfolio_amount=requested_portfolio_amount,
            fill=fill,
        )

    def simulate_sell(
        self,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        *,
        token_amount_raw: Decimal,
        position_effect: PositionEffect,
        exit_reason: str,
        signal_at: datetime,
        decision_at: datetime,
        allow_stale_market: bool = False,
        executed_at: datetime | None = None,
    ) -> PaperOrderResult:
        requested = token_amount_raw * market.observed_price_raw / _LAMPORTS_PER_SOL
        requested *= quote_price.price
        if market.execution_state is not None:
            return self._simulate_current(
                market,
                quote_price,
                side=PaperOrderSide.SELL,
                requested=requested,
                tokens=int(token_amount_raw),
                effect=position_effect,
                reason=exit_reason,
                signal_at=signal_at,
                decision_at=decision_at,
                executed_at=executed_at,
            )
        if self._policy.require_atomic_pump_state:
            return _rejected(
                PaperOrderSide.SELL,
                max(requested, Decimal("0.00000001")),
                "atomic_current_execution_state_required",
                exit_reason,
            )
        token_amount_raw = token_amount_raw.to_integral_value(rounding=ROUND_DOWN)
        if token_amount_raw <= 0:
            return _rejected(PaperOrderSide.SELL, requested, "non_positive_fill", exit_reason)
        rejection = self._validate(
            market,
            quote_price,
            executed_at or decision_at,
            allow_stale_market=allow_stale_market,
        )
        if rejection is not None:
            return _rejected(PaperOrderSide.SELL, requested, rejection, exit_reason)
        reserves = _reserves(market)
        if reserves is None:
            return _rejected(
                PaperOrderSide.SELL,
                requested,
                "reliable_market_reserves_unavailable",
                exit_reason,
            )
        quote_reserve, token_reserve = reserves
        venue_fee_bps, fee_source = effective_venue_fee_bps(
            market, fallback_bps=self._policy.venue_fee_bps
        )
        gross_quote = Decimal(quote_reserve) - (
            Decimal(quote_reserve)
            * Decimal(token_reserve)
            / (Decimal(token_reserve) + token_amount_raw)
        )
        if (
            market.real_quote_reserves_raw is not None
            and gross_quote > market.real_quote_reserves_raw
        ):
            return _rejected(
                PaperOrderSide.SELL, requested, "insufficient_real_quote_reserves", exit_reason
            )
        curve_price = gross_quote / token_amount_raw
        gross_quote *= _BPS - self._policy.latency_slippage_bps
        gross_quote /= _BPS
        gross_quote = gross_quote.to_integral_value(rounding=ROUND_DOWN)
        venue_fee = gross_quote * venue_fee_bps / _BPS
        execution_provider_fee = gross_quote * self._policy.execution_provider_fee_bps / _BPS
        net_quote = gross_quote - venue_fee - execution_provider_fee
        if net_quote <= 0:
            return _rejected(PaperOrderSide.SELL, requested, "fees_consume_order", exit_reason)
        gross_portfolio = gross_quote / _LAMPORTS_PER_SOL * quote_price.price
        fill = self._fill(
            side=PaperOrderSide.SELL,
            market=market,
            quote_price=quote_price,
            signal_at=signal_at,
            decision_at=decision_at,
            token_amount=token_amount_raw,
            gross_quote=gross_quote,
            venue_fee=venue_fee,
            execution_provider_fee=execution_provider_fee,
            requested_portfolio_amount=gross_portfolio,
            venue_fee_bps=venue_fee_bps,
            fee_source=fee_source,
            executed_at=executed_at,
            curve_price=curve_price,
            degraded_market_age_seconds=(
                max(0, int((decision_at - market.observed_at).total_seconds()))
                if allow_stale_market
                and (decision_at - market.observed_at).total_seconds()
                > self._policy.max_market_staleness_seconds
                else None
            ),
        )
        return PaperOrderResult(
            status=PaperOrderStatus.FILLED,
            side=PaperOrderSide.SELL,
            position_effect=position_effect,
            requested_portfolio_amount=requested,
            exit_reason=exit_reason,
            fill=fill,
        )

    def _simulate_current(
        self,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        *,
        side: PaperOrderSide,
        requested: Decimal,
        tokens: int | None,
        effect: PositionEffect,
        reason: str | None,
        signal_at: datetime,
        decision_at: datetime,
        executed_at: datetime | None,
    ) -> PaperOrderResult:
        at = executed_at or decision_at
        rejection = self._validate(market, quote_price, at)
        state = market.execution_state
        migration_exit = bool(state and state.get("model") == "canonical_pumpswap_exit")
        scope = entry_rejection(
            price_metadata(market, at),
            venue=market.venue.value,
            lifecycle=market.lifecycle.value,
            complete=market.curve_complete,
        )
        if migration_exit and side == PaperOrderSide.SELL:
            verified = bool(
                state
                and state.get("sell_only") is True
                and market.venue == LaunchVenue.PUMP_SWAP
                and market.normalized_state
                and market.normalized_state.execution_identity_verified
                and market.normalized_state.execution_config_verified
                and market.normalized_state.execution_assumptions_verified
                and market.normalized_state.state_quality.value == "HEALTHY"
            )
            scope = None if verified else "migration_exit_state_unverified"
        if rejection or scope:
            return _rejected(
                side,
                max(requested, Decimal("0.00000001")),
                rejection or scope or "invalid_state",
                reason,
            )
        assert state is not None
        friction = (
            self._policy.latency_slippage_bps
            + self._policy.additional_slippage_bps
            + self._policy.adverse_fill_bps
        )
        if friction >= _BPS:
            return _rejected(side, requested, "friction_consumes_order", reason)
        try:
            from .migration_exit import migration_sell_quote

            quote = (
                migration_sell_quote(state, tokens or 0)
                if migration_exit and side == PaperOrderSide.SELL
                else buy_exact_input(
                    state["curve"],
                    int(requested / quote_price.price * _LAMPORTS_PER_SOL),
                    state["rates"],
                )
                if side == PaperOrderSide.BUY
                else sell_quote(state["curve"], tokens or 0, state["rates"])
            )
        except (ValueError, KeyError):
            return _rejected(
                side, max(requested, Decimal("0.00000001")), "exact_quote_unavailable", reason
            )
        base_tokens = Decimal(quote.get("token_output", tokens or 0))
        raw_gross = Decimal(
            quote["gross_input"] if side == PaperOrderSide.BUY else quote["gross_output"]
        )
        actual_tokens = (
            (base_tokens * (1 - friction / _BPS)).to_integral_value(rounding=ROUND_DOWN)
            if side == PaperOrderSide.BUY
            else base_tokens
        )
        gross = (
            raw_gross
            if side == PaperOrderSide.BUY
            else (raw_gross * (1 - friction / _BPS)).to_integral_value(rounding=ROUND_DOWN)
        )
        lp_fee = quote.get("lp_fee", 0)
        if actual_tokens <= 0 or gross <= quote["protocol_fee"] + quote["creator_fee"] + lp_fee:
            return _rejected(side, requested, "non_positive_fill", reason)
        fees = Decimal(quote["protocol_fee"] + quote["creator_fee"] + lp_fee)
        provider_fee = raw_gross * self._policy.execution_provider_fee_bps / _BPS
        curve_price = (
            Decimal(
                quote["net_curve_input"] if side == PaperOrderSide.BUY else quote["gross_output"]
            )
            / base_tokens
        )
        fill = self._fill(
            side=side,
            market=market,
            quote_price=quote_price,
            signal_at=signal_at,
            decision_at=decision_at,
            token_amount=actual_tokens,
            gross_quote=gross,
            venue_fee=fees,
            execution_provider_fee=provider_fee,
            requested_portfolio_amount=gross / _LAMPORTS_PER_SOL * quote_price.price,
            venue_fee_bps=Decimal(
                state["rates"]["protocol_bps"]
                + state["rates"]["creator_bps"]
                + state["rates"].get("lp_bps", 0)
            ),
            fee_source="VERIFIED_ONCHAIN_ATOMIC_STATE",
            curve_price=curve_price,
            executable_price=raw_gross / base_tokens,
            executed_at=executed_at,
        )
        records = tuple(
            PaperExecutionEvidence(
                code=k,
                value=v,
                message="Current atomic execution / configurable pessimistic assumption",
            )
            for k, v in {
                "protocol_fee_raw": quote["protocol_fee"],
                "creator_fee_raw": quote["creator_fee"],
                "lp_fee_raw": lp_fee,
                "additional_slippage_bps": self._policy.additional_slippage_bps,
                "adverse_fill_bps": self._policy.adverse_fill_bps,
                "latency_penalty_bps": self._policy.latency_slippage_bps,
                "network_fee_sol": self._policy.network_fee_sol,
                "priority_fee_sol": self._policy.priority_fee_sol,
                "unadjusted_token_amount_raw": base_tokens,
                "unadjusted_gross_quote_raw": raw_gross,
                "atomic_slot": state["slot"],
                "config_version": state["binding"]["config_version"],
            }.items()
        )
        fill = fill.model_copy(
            update={
                "price_model_version": 3,
                "execution_diagnostics": {
                    "intended_route_assumption": "pumpportal_local",
                    "cost_classification": {
                        "protocol_fee": "MEASURED_OR_ONCHAIN",
                        "creator_fee": "MEASURED_OR_ONCHAIN",
                        "lp_fee": "MEASURED_OR_ONCHAIN" if migration_exit else "NOT_APPLICABLE",
                        "price_impact": "MEASURED_OR_ONCHAIN",
                        "provider_fee": "ROUTE_APPLICABLE_ESTIMATE",
                        "network_priority_fee": "ROUTE_APPLICABLE_ESTIMATE",
                        "latency_penalty": "CONSERVATIVE_SIMULATION",
                        "additional_slippage": "CONSERVATIVE_SIMULATION",
                        "adverse_fill": "CONSERVATIVE_SIMULATION",
                    },
                    "provider_fee_bps": str(self._policy.execution_provider_fee_bps),
                    "provider_fee_source": "https://pumpportal.fun/fees/",
                    "impact_basis": (
                        "quantity-specific quote using onchain reserves; independent paper bank, "
                        "not measured live impact"
                    ),
                },
                "slippage": friction,
                "evidence": fill.evidence + records,
                "execution_state": {
                    key: state[key]
                    for key in (
                        "slot",
                        "curve",
                        "rates",
                        "binding",
                        "model",
                        "sell_only",
                        "pool",
                        "reserves",
                    )
                    if key in state
                },
            }
        )
        return PaperOrderResult(
            status=PaperOrderStatus.FILLED,
            side=side,
            position_effect=effect,
            requested_portfolio_amount=max(requested, Decimal("0.00000001")),
            exit_reason=reason,
            fill=fill,
        )

    def _validate(
        self,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        decision_at: datetime,
        *,
        allow_stale_market: bool = False,
    ) -> str | None:
        if market.rpc_state == "degraded" and not allow_stale_market:
            return "execution_rpc_state_unavailable"
        if market.curve_complete:
            return "bonding_curve_complete_wait_for_migration"
        if market.quote_asset != quote_price.quote_asset:
            return "quote_asset_mismatch"
        if market.real_token_reserves_raw is None or market.real_quote_reserves_raw is None:
            return "reliable_market_reserves_unavailable"
        market_age = (decision_at - market.observed_at).total_seconds()
        if market_age < 0:
            return "market_snapshot_after_decision"
        if market_age > self._policy.max_market_staleness_seconds and not allow_stale_market:
            return "market_snapshot_stale"
        quote_age = (decision_at - quote_price.provenance.observed_at).total_seconds()
        if quote_age > self._policy.max_quote_price_staleness_seconds:
            return "quote_price_stale"
        if quote_age < 0:
            return "quote_price_timestamp_after_decision"
        return None

    def _fill(
        self,
        *,
        side: PaperOrderSide,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        signal_at: datetime,
        decision_at: datetime,
        token_amount: Decimal,
        gross_quote: Decimal,
        venue_fee: Decimal,
        execution_provider_fee: Decimal,
        requested_portfolio_amount: Decimal,
        venue_fee_bps: Decimal,
        fee_source: str,
        curve_price: Decimal,
        executed_at: datetime | None = None,
        degraded_market_age_seconds: int | None = None,
        executable_price: Decimal | None = None,
    ) -> PaperFill:
        submitted_at = decision_at + timedelta(milliseconds=self._policy.compute_latency_ms)
        filled_at = executed_at or submitted_at + timedelta(
            milliseconds=self._policy.submission_latency_ms
        )
        if executed_at is not None and executed_at < submitted_at + timedelta(
            milliseconds=self._policy.submission_latency_ms
        ):
            raise ValueError("execution_precedes_submission")
        network_fee_quote = (
            self._policy.network_fee_sol + self._policy.priority_fee_sol
        ) * _LAMPORTS_PER_SOL
        total_fee_portfolio = (
            (venue_fee + execution_provider_fee + network_fee_quote)
            / _LAMPORTS_PER_SOL
            * quote_price.price
        )
        actual_price = gross_quote / token_amount
        expected_price = executable_price or curve_price
        reserves = _reserves(market)
        assert reserves is not None
        spot = Decimal(reserves[0]) / Decimal(reserves[1])
        price_impact = abs(curve_price / spot - Decimal(1)) * _BPS
        provenance = ProviderProvenance(
            provider="bullseye_constant_product_simulator",
            observed_at=market.observed_at,
            received_at=market.received_timestamp or market.observed_at,
            confidence=DataConfidence.ESTIMATED,
            source_reference=(
                f"slot:{market.source_slot}" if market.source_slot is not None else None
            ),
        )
        return PaperFill(
            price_model_version=2,
            **price_metadata(market, filled_at),
            decision_price=market.decision_price or market.observed_price_raw,
            reference_price=spot,
            executable_quote=expected_price,
            simulated_fill=actual_price,
            price_impact=price_impact,
            slippage=self._policy.latency_slippage_bps,
            fees=total_fee_portfolio,
            signal_at=signal_at,
            decision_at=decision_at,
            submitted_at=submitted_at,
            filled_at=filled_at,
            market_observed_at=market.observed_at,
            quote_price_observed_at=quote_price.provenance.observed_at,
            quote_asset=market.quote_asset,
            portfolio_currency=quote_price.portfolio_currency,
            quote_price_in_portfolio_currency=quote_price.price,
            observed_price_raw=market.observed_price_raw,
            expected_fill_price_raw=expected_price,
            actual_fill_price_raw=actual_price,
            token_amount_raw=token_amount,
            gross_quote_amount_raw=gross_quote,
            gross_portfolio_amount=requested_portfolio_amount,
            venue_fee_quote_raw=venue_fee,
            execution_provider_fee_quote_raw=execution_provider_fee,
            network_fee_quote_raw=network_fee_quote,
            total_fee_portfolio=total_fee_portfolio,
            price_impact_bps=price_impact,
            total_price_deviation_bps=abs(actual_price / expected_price - Decimal(1)) * _BPS,
            latency_slippage_bps=self._policy.latency_slippage_bps,
            simulated_latency_ms=(
                self._policy.compute_latency_ms + self._policy.submission_latency_ms
            ),
            fill_quality=(
                FillQuality.DEGRADED
                if degraded_market_age_seconds is not None
                else FillQuality.ESTIMATED
            ),
            evidence=(
                PaperExecutionEvidence(
                    code="constant_product_reserves",
                    value=(
                        "quote="
                        f"{market.virtual_quote_reserves_raw or market.real_quote_reserves_raw};"
                        "token="
                        f"{market.virtual_token_reserves_raw or market.real_token_reserves_raw}"
                    ),
                    message="Execution snapshot reserves used for quantity-specific price impact",
                    provenance=provenance,
                ),
                PaperExecutionEvidence(
                    code="effective_venue_fee_bps",
                    value=venue_fee_bps,
                    message=f"Decision-time venue fee assumption: {fee_source}",
                ),
                PaperExecutionEvidence(
                    code="execution_provider_fee_bps",
                    value=self._policy.execution_provider_fee_bps,
                    message="PumpPortal Local API service-fee assumption",
                ),
                PaperExecutionEvidence(
                    code="pump_market_cap_sol",
                    value=(
                        pump_market_cap_sol(market.observed_price_raw)
                        if market.venue.value in {"pump_fun", "pump_swap"}
                        else None
                    ),
                    message="Market cap used for the canonical PumpSwap fee tier",
                ),
                PaperExecutionEvidence(
                    code="configured_latency_slippage_bps",
                    value=self._policy.latency_slippage_bps,
                    message="Conservative latency slippage assumption",
                ),
                PaperExecutionEvidence(
                    code="side",
                    value=side.value,
                    message="Simulated paper order direction",
                ),
            )
            + (
                (
                    PaperExecutionEvidence(
                        code="forced_stale_market_age_seconds",
                        value=degraded_market_age_seconds,
                        message=(
                            "Operator explicitly forced a paper close using the last "
                            "known market snapshot"
                        ),
                    ),
                )
                if degraded_market_age_seconds is not None
                else ()
            ),
        )


def _reserves(market: ExecutionMarketSnapshot) -> tuple[int, int] | None:
    quote = market.virtual_quote_reserves_raw
    token = market.virtual_token_reserves_raw
    if quote is None or token is None:
        quote = (
            market.real_quote_reserves_raw + (market.virtual_quote_reserves_raw or 0)
            if market.real_quote_reserves_raw is not None
            else None
        )
        token = market.real_token_reserves_raw
    if quote is None or token is None or quote <= 0 or token <= 0:
        return None
    return quote, token


def _rejected(
    side: PaperOrderSide,
    requested: Decimal,
    reason: str,
    exit_reason: str | None = None,
) -> PaperOrderResult:
    return PaperOrderResult(
        status=PaperOrderStatus.REJECTED,
        side=side,
        position_effect=PositionEffect.NONE,
        requested_portfolio_amount=max(requested, Decimal("0.00000001")),
        rejection_reason=reason,
        exit_reason=exit_reason,
    )
