from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from time import perf_counter
from typing import Any
from uuid import UUID, uuid5

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.logging import get_logger
from memebot.eligibility import paper_candidate_rejection
from memebot.events.models import (
    DomainEvent,
    MarketFeatureSnapshotCreated,
    PaperActionPending,
    PaperOrderCompleted,
    StrategyDecisionCreated,
    TokenTrade,
)
from memebot.intelligence.ollama_policy import OllamaPaperPolicy
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import (
    PaperFill,
    PaperOrderResult,
    PaperOrderSide,
    PaperOrderStatus,
    PositionEffect,
)
from memebot.models.strategy import StrategyDecisionAction
from memebot.providers.price.base import QuotePrice, QuotePriceProvider
from memebot.providers.price.coingecko import QuotePriceError
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.pulse.service import PulseService
from memebot.storage.database.control import ControlRepository, TradingControlSnapshot
from memebot.storage.database.pending import (
    PendingPaperAction,
    PendingPaperActionRepository,
)
from memebot.storage.database.registry import TokenRegistry

from .dump_hazard import has_dump_hazard
from .execution import ExecutionPolicy, PaperFillSimulator
from .exits import ExitIntent, exit_intent
from .market_refresh import MarketSnapshotRefresher
from .models import ExecutionMarketSnapshot, PortfolioSnapshot, PositionSnapshot
from .price_safety import entry_data_block, price_metadata, with_price_evidence
from .risk_governor import PortfolioRiskGovernor

_PAPER_EVENT_NAMESPACE = UUID("30dd8790-ee2d-5182-8280-e365355da6f2")
type EventPublisher = Callable[[DomainEvent], Awaitable[object]]


class PaperTradingEngine:
    """Decision-to-paper-fill boundary. It has no signer or transaction client."""

    def __init__(
        self,
        settings: Settings,
        registry: TokenRegistry,
        controls: ControlRepository,
        pending: PendingPaperActionRepository,
        quote_prices: QuotePriceProvider,
        publish: EventPublisher,
        *,
        entry_thresholds: dict[str, Decimal],
        market_refresher: MarketSnapshotRefresher | None = None,
        exit_market_refresher: MarketSnapshotRefresher | None = None,
        pulse: PulseService | None = None,
        ollama_policy: OllamaPaperPolicy | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._controls = controls
        self._pending = pending
        self._quote_prices = quote_prices
        self._event_sink = publish
        self._publish = self._publish_event
        self._entry_thresholds = entry_thresholds
        self._market_refresher = market_refresher
        self._exit_market_refresher = exit_market_refresher or market_refresher
        self._pulse = pulse
        self._ollama_policy = ollama_policy
        self._logger = get_logger("memebot.paper")
        self._last_logged_mark_prices: dict[str, Decimal] = {}
        self._hazard_since: dict[str, datetime] = {}
        self._entry_lock = asyncio.Lock()
        self._position_locks: dict[str, asyncio.Lock] = {}
        self._exit_tasks: dict[str, asyncio.Task[None]] = {}
        self._exit_wakes: dict[str, tuple[int | None, datetime, float]] = {}
        self._closed_for_exits = False
        self._risk_governor = PortfolioRiskGovernor(settings, registry)
        self._simulator = PaperFillSimulator(
            ExecutionPolicy(
                venue_fee_bps=settings.paper_venue_fee_bps,
                latency_slippage_bps=settings.paper_latency_slippage_bps,
                network_fee_sol=settings.paper_network_fee_sol,
                priority_fee_sol=settings.paper_priority_fee_sol,
                compute_latency_ms=settings.paper_compute_latency_ms,
                submission_latency_ms=settings.paper_submission_latency_ms,
                max_market_staleness_seconds=settings.paper_max_market_staleness_seconds,
                max_quote_price_staleness_seconds=(
                    settings.paper_max_quote_price_staleness_seconds
                ),
                execution_provider_fee_bps=settings.paper_execution_provider_fee_bps,
                additional_slippage_bps=settings.paper_additional_slippage_bps,
                adverse_fill_bps=settings.paper_adverse_fill_bps,
                require_atomic_pump_state=True,
            )
        )

    async def on_decision(
        self,
        event: StrategyDecisionCreated,
        *,
        pending_action: PendingPaperAction | None = None,
        retry_trigger: TokenTrade | None = None,
    ) -> None:
        async with self._entry_lock:
            await self._on_decision(
                event,
                pending_action=pending_action,
                retry_trigger=retry_trigger,
            )

    async def _publish_event(self, event: DomainEvent) -> object:
        if isinstance(event, PaperOrderCompleted) and self._settings.execution_mode == "shadow":
            event = event.model_copy(update={"shadow_only": True})
            if event.result.fill is not None:
                self._logger.info(
                    f"would_{event.result.side.value}",
                    mint=event.mint,
                    decision_event_id=str(event.decision_event_id),
                    reason=event.result.exit_reason,
                )
        return await self._event_sink(event)

    async def _on_decision(
        self,
        event: StrategyDecisionCreated,
        *,
        pending_action: PendingPaperAction | None = None,
        retry_trigger: TokenTrade | None = None,
    ) -> None:
        if (
            not self._settings.paper_trading_enabled
            or not event.active_strategy
            or event.action != StrategyDecisionAction.ENTER_CANDIDATE
        ):
            return
        control = await self._controls.get()
        if control is None:
            await self._cancel_pending(pending_action, "trading_control_unavailable")
            return
        if pending_action is not None and control.active_strategy_key != event.strategy_key:
            await self._cancel_pending(pending_action, "active_strategy_changed")
            return
        portfolio = await self._registry.active_paper_portfolio()
        if portfolio is None:
            await self._cancel_pending(pending_action, "active_paper_portfolio_not_found")
            return
        if control.entries_paused or self._settings.signal_mode:
            reason = (
                "signal_mode_no_auto_entries" if self._settings.signal_mode else "entries_paused"
            )
            market = await self._registry.paper_market_context(event.mint, as_of=utc_now())
            await self._publish_rejection(event, portfolio, market, reason)
            await self._cancel_pending(pending_action, reason)
            return
        momentum = next((item for item in event.score.components if item.name == "momentum"), None)
        if (
            event.decision_price is None
            or event.decision_price <= 0
            or momentum is None
            or momentum.component_status != "COMPLETE"
            or momentum.missing_required_inputs
            or event.price_evidence.get("observational_trust") != "OBSERVATIONAL_HEALTHY"
            or event.price_evidence.get("continuity_status")
            not in {"FIRST_OBSERVATION", "EXACT", "RPC_VALIDATED"}
            or event.price_evidence.get("data_quality")
            not in {"source_time_reported", "canonical_atomic_bank_verified"}
        ):
            await self._publish_rejection(
                event, portfolio, None, "REQUIRED_PRICE_SIGNAL_INCOMPLETE"
            )
            await self._cancel_pending(pending_action, "REQUIRED_PRICE_SIGNAL_INCOMPLETE")
            return
        if pending_action is None:
            pending_action = await self._pending.pending_for_mint(
                event.mint, action="automatic_entry"
            )
        market = await self._registry.paper_market_context(event.mint, as_of=utc_now())
        universe_block = paper_candidate_rejection(event.price_evidence)
        if universe_block is not None:
            await self._publish_rejection(event, portfolio, market, universe_block)
            await self._cancel_pending(pending_action, universe_block)
            return
        if await self._controls.is_blacklisted(event.mint):
            await self._publish_rejection(event, portfolio, market, "token_blacklisted")
            await self._cancel_pending(pending_action, "token_blacklisted")
            return
        alpha_snapshot = await self._registry.alpha_filter_snapshot(event.mint)
        alpha_blocking = (
            alpha_snapshot.get("blocking_reasons") if isinstance(alpha_snapshot, dict) else None
        )
        alpha_shadow_mode = (
            alpha_snapshot.get("shadow_mode") if isinstance(alpha_snapshot, dict) else None
        )
        if alpha_shadow_mode is not True and isinstance(alpha_blocking, list) and alpha_blocking:
            reason = f"alpha_filter:{str(alpha_blocking[0])[:96]}"
            await self._publish_rejection(event, portfolio, market, reason)
            await self._cancel_pending(pending_action, reason)
            return
        if await self._registry.open_position(event.mint) is not None:
            await self._publish_rejection(event, portfolio, market, "position_already_open")
            await self._cancel_pending(pending_action, "position_already_open")
            return
        if portfolio.open_position_count >= control.max_open_positions:
            await self._publish_rejection(
                event, portfolio, market, "maximum_open_positions_reached"
            )
            await self._cancel_pending(pending_action, "maximum_open_positions_reached")
            return
        if market is None:
            await self._publish_rejection(event, portfolio, None, "market_state_unavailable")
            await self._cancel_pending(pending_action, "market_state_unavailable")
            return
        if market.quote_asset != WRAPPED_SOL_MINT:
            await self._publish_rejection(event, portfolio, market, "unsupported_quote_asset")
            await self._cancel_pending(pending_action, "unsupported_quote_asset")
            return
        strategy_price = event.decision_price or market.observed_price_raw
        market = await self._refresh_market(market)
        data_block = entry_data_block(market, utc_now(), self._settings)
        if data_block is not None:
            await self._publish_rejection(event, portfolio, market, data_block)
            await self._cancel_pending(pending_action, data_block)
            return
        score = event.score.final_score
        if score is None:
            await self._publish_rejection(event, portfolio, market, "score_unknown")
            await self._cancel_pending(pending_action, "score_unknown")
            return
        requested = self._position_size(portfolio, score, event.strategy_key, control)
        if self._ollama_policy is not None:
            if event.requested_position_percent is None:
                await self._publish_rejection(event, portfolio, market, "llm_allocation_missing")
                return
            capital = min(portfolio.initial_cash, portfolio.initial_cash + portfolio.realized_pnl)
            requested = min(
                max(Decimal(0), capital)
                * min(event.requested_position_percent, control.max_position_percent)
                / Decimal(100),
                portfolio.cash_balance,
                max(Decimal(0), capital)
                * self._settings.paper_risk_per_trade_percent
                / max(
                    control.stop_loss_percent, self._settings.paper_stop_loss_risk_reserve_percent
                ),
            ).quantize(Decimal("0.00000001"))
        if requested <= 0:
            await self._publish_rejection(event, portfolio, market, "portfolio_cash_unavailable")
            await self._cancel_pending(pending_action, "portfolio_cash_unavailable")
            return
        try:
            quote_price = await self._quote_prices.quote_price(portfolio.currency)
        except QuotePriceError:
            await self._publish_rejection(event, portfolio, market, "quote_price_unavailable")
            await self._cancel_pending(pending_action, "quote_price_unavailable")
            return
        if self._settings.paper_sizing_mode == "sol_tiers":
            requested = self._sol_tier_size(portfolio, score, quote_price.price, control)
        decision_at = utc_now()
        signal_at = (
            await self._registry.feature_observed_at(event.feature_event_id)
            if event.feature_event_id is not None
            else None
        ) or event.source_event_at
        if (
            decision_at - _aware(signal_at)
        ).total_seconds() > self._settings.paper_max_signal_age_seconds:
            await self._publish_rejection(event, portfolio, market, "entry_signal_expired")
            await self._cancel_pending(pending_action, "entry_signal_expired")
            return
        signal_price = market.observed_price_raw
        await self._execution_delay()
        market = await self._refresh_market(market)
        market = replace(market, decision_price=strategy_price)
        data_block = entry_data_block(market, utc_now(), self._settings)
        if data_block is not None:
            await self._publish_rejection(event, portfolio, market, data_block)
            await self._cancel_pending(pending_action, data_block)
            return
        if self._settings.pulse_enabled and self._pulse is not None:
            pulse_reason = await self._pulse.entry_rejection(event.mint, market=market)
            if pulse_reason is not None:
                await self._publish_rejection(event, portfolio, market, pulse_reason)
                await self._cancel_pending(pending_action, pulse_reason)
                return
        execution_at = utc_now()
        if (
            execution_at - _aware(signal_at)
        ).total_seconds() > self._settings.paper_max_signal_age_seconds:
            await self._publish_rejection(
                event, portfolio, market, "entry_signal_expired_before_fill"
            )
            await self._cancel_pending(pending_action, "entry_signal_expired_before_fill")
            return
        refreshed_control = await self._controls.get()
        if (
            refreshed_control is None
            or refreshed_control.entries_paused
            or refreshed_control != control
        ):
            await self._publish_rejection(event, portfolio, market, "control_changed_before_fill")
            await self._cancel_pending(pending_action, "control_changed_before_fill")
            return
        if (
            abs(market.observed_price_raw / signal_price - 1) * 100
            > self._settings.paper_max_signal_price_drift_percent
        ):
            await self._publish_rejection(event, portfolio, market, "entry_price_moved_before_fill")
            await self._cancel_pending(pending_action, "entry_price_moved_before_fill")
            return
        capacity_check = await self._risk_governor.assess_entry(
            event.mint, Decimal(0), as_of=execution_at
        )
        if not capacity_check.allowed:
            reason = capacity_check.rejection_reason or "portfolio_risk_gate_rejected"
            await self._publish_rejection(event, portfolio, market, reason)
            await self._cancel_pending(pending_action, reason)
            if capacity_check.circuit_breaker_tripped:
                await self._pause_for_daily_loss_limit()
            return
        entry_budget = min(
            portfolio.cash_balance, capacity_check.remaining_entry_capacity or Decimal(0)
        )
        requested, result = self._liquidity_adjusted_buy(
            portfolio=portfolio,
            control=control,
            strategy_key=event.strategy_key,
            target=requested,
            market=market,
            quote_price=quote_price,
            signal_at=signal_at,
            decision_at=decision_at,
            executed_at=execution_at,
            available_budget=entry_budget,
        )
        if result.rejection_reason == "market_snapshot_stale":
            if pending_action is None:
                pending_action = await self._pending.enqueue(
                    portfolio_id=portfolio.portfolio_id,
                    mint=event.mint,
                    action="automatic_entry",
                    ttl_seconds=self._settings.paper_pending_entry_ttl_seconds,
                    decision_event_id=event.event_id,
                )
                if pending_action.is_new:
                    await self._publish(
                        PaperActionPending(
                            provider="bullseye_paper_engine",
                            source_event_at=utc_now(),
                            correlation_id=event.correlation_id or event.event_id,
                            portfolio_id=portfolio.portfolio_id,
                            mint=event.mint,
                            action="entry",
                            expires_at=pending_action.expires_at,
                            reason="market_snapshot_stale",
                            decision_event_id=event.event_id,
                        )
                    )
            return
        if result.fill is not None:
            risk_assessment = await self._risk_governor.assess_entry(
                event.mint, self._entry_cash_cost(result), as_of=utc_now()
            )
            if not risk_assessment.allowed:
                reason = risk_assessment.rejection_reason or "portfolio_risk_gate_rejected"
                if risk_assessment.circuit_breaker_tripped:
                    await self._pause_for_daily_loss_limit()
                result = _rejection(PaperOrderSide.BUY, requested, reason)
        if result.fill is not None:
            non_curve_fees = (
                (result.fill.network_fee_quote_raw + result.fill.execution_provider_fee_quote_raw)
                / Decimal(1_000_000_000)
                * quote_price.price
            )
            if result.fill.gross_portfolio_amount + non_curve_fees > portfolio.cash_balance:
                result = _rejection(
                    PaperOrderSide.BUY,
                    requested,
                    "portfolio_cash_insufficient_for_fees",
                )
        completed = _paper_event(
            trigger_event=retry_trigger or event,
            portfolio=portfolio,
            market=market,
            result=result,
            strategy_key=event.strategy_key,
            decision_event_id=event.event_id,
            kind=(
                f"entry_retry:{retry_trigger.event_id}" if retry_trigger is not None else "entry"
            ),
        )
        await self._publish(completed)
        if pending_action is not None:
            await self._pending.finish(
                pending_action.id,
                status="completed" if result.status == PaperOrderStatus.FILLED else "cancelled",
                reason=result.rejection_reason or "filled_on_fresh_trade",
                completion_event_id=completed.event_id,
            )

    async def on_trade(
        self,
        event: TokenTrade,
        feature: MarketFeatureSnapshotCreated | None = None,
    ) -> None:
        if not self._settings.paper_trading_enabled:
            return
        # Entry retries never hold the exit monitor's lock during RPC/model waits.
        position = await self._registry.open_position(event.mint)
        if position is None:
            await self._retry_pending_entry(event)
            return
        if event.source_event_at >= _aware(position.opened_at):
            await self._protect_position(position, event=event, feature=feature)

    def wake_open_position(self, mint: str, slot: int | None, received_at: datetime) -> None:
        """Receipt-only priority wake; only a fresh atomic read can authorize a sell."""
        if self._closed_for_exits:
            return
        self._exit_wakes[mint] = (slot, received_at, perf_counter())
        if mint not in self._exit_tasks:
            self._exit_tasks[mint] = asyncio.create_task(self._drain_exit_wakes(mint))

    async def _drain_exit_wakes(self, mint: str) -> None:
        try:
            while mint in self._exit_wakes:
                slot, received_at, queued = self._exit_wakes.pop(mint)
                position = await self._registry.open_position(mint)
                if position is None:
                    self._exit_wakes.pop(mint, None)
                    break
                await self._protect_position(
                    position,
                    trace={
                        "event_received_at": received_at.isoformat() if slot is not None else None,
                        "event_ingested_at": None,
                        "event_ingested_status": "receipt_only_wake"
                        if slot is not None
                        else "watchdog",
                        "trigger_slot": slot,
                        "queue_wait_ms": (perf_counter() - queued) * 1000,
                    },
                )
        except Exception as error:
            self._logger.error(
                "priority_exit_evaluation_failed", mint=mint, error_type=type(error).__name__
            )
        finally:
            self._exit_tasks.pop(mint, None)

    async def _protect_position(
        self,
        position: PositionSnapshot,
        *,
        event: TokenTrade | None = None,
        feature: MarketFeatureSnapshotCreated | None = None,
        trace: dict[str, Any] | None = None,
    ) -> None:
        lock = self._position_locks.setdefault(position.mint, asyncio.Lock())
        started = perf_counter()
        trace = dict(
            trace
            or {
                "event_received_at": (event.provider_received_at or event.ingested_at).isoformat()
                if event
                else None,
                "event_ingested_at": event.ingested_at.isoformat() if event else None,
                "event_ingested_status": "ingested" if event else "watchdog",
                "trigger_slot": event.source_slot if event else None,
                "queue_wait_ms": max(
                    0,
                    (utc_now() - (event.provider_received_at or event.ingested_at)).total_seconds()
                    * 1000,
                )
                if event
                else 0,
            }
        )
        async with lock:
            trace.update(
                lock_wait_ms=(perf_counter() - started) * 1000,
                exit_evaluation_started_at=utc_now().isoformat(),
            )
            current = await self._registry.open_position(position.mint)
            if current is None or current.position_id != position.position_id:
                return
            if event is not None and await self._execute_pending_manual_close(event):
                return
            async with asyncio.timeout(self._settings.paper_exit_recovery_attempt_timeout_seconds):
                await self._evaluate_position(current, event=event, feature=feature, trace=trace)

    async def _refresh_exit_market(
        self, market: ExecutionMarketSnapshot, trace: dict[str, Any]
    ) -> ExecutionMarketSnapshot:
        started_at, started = utc_now(), perf_counter()
        trace.setdefault("RPC_refresh_started_at", started_at.isoformat())
        refreshed = await self._refresh_market(market, for_exit=True)
        elapsed = (perf_counter() - started) * 1000
        trace["RPC_refresh_completed_at"] = utc_now().isoformat()
        trace["RPC_ms"] = float(trace.get("RPC_ms", 0)) + elapsed
        trace.setdefault("RPC_reads", []).append(
            {
                "started_at": started_at.isoformat(),
                "completed_at": trace["RPC_refresh_completed_at"],
                "ms": elapsed,
                "slot": refreshed.source_slot,
                "quality": refreshed.data_quality,
            }
        )
        return refreshed

    def _exit_diagnostics(
        self,
        position: PositionSnapshot,
        fill: PaperFill,
        control: TradingControlSnapshot,
        trace: dict[str, Any],
        *,
        risk_fill: PaperFill | None = None,
    ) -> PaperFill:
        risk_quote = risk_fill or fill
        net = risk_quote.gross_portfolio_amount - risk_quote.total_fee_portfolio
        risk = (net / position.remaining_cost_basis - 1) * 100
        gross = (fill.actual_fill_price_raw / position.entry_price_raw - 1) * 100
        settings = self._settings
        activation = (
            settings.paper_runner_trailing_activation_percent
            if settings.paper_runner_enabled
            else settings.paper_trailing_activation_percent
        )
        common = {
            "stop_percent": str(control.stop_loss_percent),
            "take_profit_fraction": str(settings.paper_take_profit_fraction),
            "max_holding_seconds": control.max_holding_seconds,
            "stagnation_seconds": settings.paper_stagnation_exit_seconds,
            "stagnation_min_mfe_percent": str(settings.paper_stagnation_min_mfe_percent),
        }
        policies = {
            "CURRENT_POLICY": {
                **common,
                "take_profit_percent": str(control.take_profit_percent),
                "activation_percent": str(activation),
                "width_percent": str(control.trailing_stop_percent),
                "runner_enabled": settings.paper_runner_enabled,
                "runner_min_width": str(settings.paper_runner_trailing_min_percent),
                "runner_max_width": str(settings.paper_runner_trailing_max_percent),
                "runner_max_holding_seconds": settings.paper_runner_max_holding_seconds,
            },
            "EARLIER_PROFIT_PROTECTION": {
                **common,
                "take_profit_percent": str(control.take_profit_percent / 2),
                "activation_percent": str(activation / 2),
                "width_percent": str(control.trailing_stop_percent),
            },
            "DEFENSIVE_PROFIT_PROTECTION": {
                **common,
                "take_profit_percent": str(control.take_profit_percent / 4),
                "activation_percent": str(activation / 4),
                "width_percent": str(control.trailing_stop_percent / 2),
            },
        }
        return fill.model_copy(
            update={
                "exit_telemetry": dict(trace),
                "execution_diagnostics": {
                    **fill.execution_diagnostics,
                    "net_liquidation_value": str(net),
                    "gross_price_change_percent": str(gross),
                    "net_executable_pnl_percent": str(risk),
                    "stop_metric": "NET_EXECUTABLE_REMAINING_COST_BASIS",
                    "provider_fee_bps": str(settings.paper_execution_provider_fee_bps),
                    "shadow_policies": policies,
                },
            }
        )

    async def _retry_pending_entry(
        self,
        event: TokenTrade,
    ) -> None:
        pending_entry = await self._pending.pending_for_mint(event.mint, action="automatic_entry")
        if pending_entry is not None:
            if pending_entry.decision is None:
                await self._pending.finish(
                    pending_entry.id,
                    status="cancelled",
                    reason="strategy_decision_unavailable",
                )
            else:
                await self.on_decision(
                    pending_entry.decision,
                    pending_action=pending_entry,
                    retry_trigger=event,
                )
            return

    async def _evaluate_position(
        self,
        position: PositionSnapshot,
        *,
        event: TokenTrade | None = None,
        feature: MarketFeatureSnapshotCreated | None = None,
        trace: dict[str, Any] | None = None,
    ) -> None:
        trace = trace if trace is not None else {}
        control = await self._controls.get()
        portfolio = await self._registry.active_paper_portfolio()
        if control is None or portfolio is None or portfolio.portfolio_id != position.portfolio_id:
            return
        market = await self._registry.paper_market_context(position.mint, as_of=utc_now())
        if market is None:
            market = ExecutionMarketSnapshot(
                position.mint,
                position.market,
                position.venue,
                position.lifecycle,
                _aware(position.opened_at),
                None,
                position.entry_price_raw,
                WRAPPED_SOL_MINT,
                None,
                None,
                None,
                None,
                data_quality="feed_context_unavailable",
            )
        if market.quote_asset != WRAPPED_SOL_MINT:
            await self._record_exit_recovery(position, portfolio, market, "unsupported_quote_asset")
            return
        market = replace(
            market,
            source_slot=max(
                market.source_slot or 0,
                int(trace.get("trigger_slot") or 0),
                int((position.execution_mark or {}).get("state_slot") or 0),
            ),
        )
        market = await self._refresh_exit_market(market, trace)
        if (
            market.observed_at < _aware(position.opened_at)
            or not 0
            <= (utc_now() - market.observed_at).total_seconds()
            <= self._settings.paper_max_market_staleness_seconds
        ):
            self._logger.error(
                "exit_recovery_market_unavailable",
                mint=position.mint,
                **price_metadata(market, utc_now()),
            )
            await self._record_exit_recovery(position, portfolio, market, "market_snapshot_stale")
            return
        try:
            mark_quote = await self._quote_prices.quote_price(portfolio.currency)
        except QuotePriceError:
            self._logger.error("exit_recovery_quote_unavailable", mint=position.mint)
            await self._record_exit_recovery(position, portfolio, market, "quote_price_unavailable")
            return
        executable_mark = self._simulator.simulate_sell(
            market,
            mark_quote,
            token_amount_raw=position.token_quantity_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="execution_mark",
            signal_at=utc_now(),
            decision_at=utc_now(),
        )
        if executable_mark.fill is None:
            self._logger.error(
                "exit_recovery_quote_incomplete",
                mint=position.mint,
                reason=executable_mark.rejection_reason,
            )
            await self._record_exit_recovery(
                position,
                portfolio,
                market,
                executable_mark.rejection_reason or "executable_quote_incomplete",
            )
            return
        # Gross executable sell price shares the entry fill unit. Fees remain explicit.
        mark_price = executable_mark.fill.actual_fill_price_raw
        mark_fill = self._exit_diagnostics(position, executable_mark.fill, control, trace)
        net_return = Decimal(mark_fill.execution_diagnostics["net_executable_pnl_percent"])
        market = replace(market, decision_price=mark_price)
        hazard = False
        if event is not None:
            if has_dump_hazard(event, feature):
                first = self._hazard_since.setdefault(position.mint, event.source_event_at)
                hazard = (
                    event.source_event_at - first
                ).total_seconds() >= self._settings.paper_hazard_confirmation_seconds
            else:
                self._hazard_since.pop(position.mint, None)
        await self._registry.observe_open_position_price(
            position.position_id,
            mark_price,
            observed_at=market.observed_at,
            execution_fill=mark_fill,
        )
        await self._pause_if_daily_loss_limit_reached(utc_now())
        llm_reason: str | None = None
        protective_intent = exit_intent(
            position,
            mark_price,
            utc_now(),
            control,
            self._settings,
            hazard=hazard,
            net_executable_pnl_percent=net_return,
        )
        emergency = protective_intent is not None and protective_intent.reason in {
            "stop_loss",
            "dump_hazard",
            "maximum_holding_time",
        }
        if emergency:
            intent = protective_intent
        elif self._ollama_policy is not None:
            try:
                choice = await self._ollama_policy.exit(position, market, feature, portfolio)
                llm_reason = choice.reason
                intent = (
                    None
                    if choice.action == "hold"
                    else ExitIntent(
                        "llm_sell" if choice.action == "sell" else "llm_partial_sell",
                        PositionEffect.CLOSE
                        if choice.action == "sell"
                        else PositionEffect.PARTIAL_CLOSE,
                        position.token_quantity_raw * choice.sell_percent / Decimal(100),
                    )
                )
                self._logger.info(
                    "ollama_exit_decision",
                    mint=position.mint,
                    action=choice.action,
                    sell_percent=str(choice.sell_percent),
                    reason=choice.reason,
                )
            except Exception as exc:
                self._logger.warning(
                    "ollama_exit_unavailable",
                    mint=position.mint,
                    error_type=type(exc).__name__,
                    detail=str(exc)[:160],
                )
                return
        else:
            intent = exit_intent(
                position,
                mark_price,
                utc_now(),
                control,
                self._settings,
                hazard=hazard,
                net_executable_pnl_percent=net_return,
            )
        if intent is None:
            return
        trigger_price = mark_price
        trace["exit_triggered_at"] = utc_now().isoformat()
        trace["trigger_reason"] = intent.reason
        trace["trigger_net_executable_pnl_percent"] = str(net_return)
        trace["trigger_gross_price"] = str(mark_price)
        decision_at = utc_now()
        delay_started = perf_counter()
        await self._execution_delay()
        trace["simulated_execution_delay_ms"] = (perf_counter() - delay_started) * 1000
        trace["configured_execution_delay_ms"] = (
            self._settings.paper_compute_latency_ms + self._settings.paper_submission_latency_ms
        )
        market = await self._refresh_exit_market(market, trace)
        current_position = await self._registry.open_position(position.mint)
        if current_position is None or current_position.position_id != position.position_id:
            return
        position = current_position
        current_control = await self._controls.get()
        if current_control is None:
            return
        control = current_control
        try:
            mark_quote = await self._quote_prices.quote_price(portfolio.currency)
        except QuotePriceError:
            await self._record_exit_recovery(position, portfolio, market, "quote_price_unavailable")
            return
        refreshed_mark = self._simulator.simulate_sell(
            market,
            mark_quote,
            token_amount_raw=position.token_quantity_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="execution_mark",
            signal_at=decision_at,
            decision_at=utc_now(),
        )
        if refreshed_mark.fill is None:
            await self._publish(
                _paper_monitor_event(
                    position=position,
                    portfolio=portfolio,
                    market=market,
                    result=refreshed_mark,
                    exit_reason="exit_recovery",
                )
            )
            return
        mark_price = refreshed_mark.fill.actual_fill_price_raw
        refreshed_fill = self._exit_diagnostics(position, refreshed_mark.fill, control, trace)
        net_return = Decimal(refreshed_fill.execution_diagnostics["net_executable_pnl_percent"])
        # Re-evaluate soft exits on execution-time state. No stale trigger is a forced sell.
        # A triggered stop-loss sells immediately; a brief bounce does not cancel it.
        if intent.reason == "stop_loss":
            pass
        elif emergency or self._ollama_policy is None:
            intent = exit_intent(
                position,
                mark_price,
                utc_now(),
                control,
                self._settings,
                hazard=hazard and mark_price <= trigger_price,
                net_executable_pnl_percent=net_return,
            )
        elif (
            abs(mark_price / trigger_price - 1) * 100
            > self._settings.paper_max_signal_price_drift_percent
        ):
            return
        if intent is None:
            return
        result = self._simulator.simulate_sell(
            market,
            mark_quote,
            token_amount_raw=intent.quantity,
            position_effect=intent.effect,
            exit_reason=intent.reason,
            signal_at=event.source_event_at if event else decision_at,
            decision_at=decision_at,
            executed_at=utc_now(),
        )
        if result.fill is not None:
            trace["paper_fill_at"] = result.fill.filled_at.isoformat()
            trace["trigger_to_fill_ms"] = (
                result.fill.filled_at - datetime.fromisoformat(trace["exit_triggered_at"])
            ).total_seconds() * 1000
            trace["price_change_trigger_to_fill_percent"] = str(
                (result.fill.actual_fill_price_raw / trigger_price - 1) * 100
            )
            final_fill = self._exit_diagnostics(
                position, result.fill, control, trace, risk_fill=refreshed_mark.fill
            )
            result = result.model_copy(update={"fill": final_fill})
            # Retain the final executable bank as well as the detection bank.
            await self._registry.observe_open_position_price(
                position.position_id,
                refreshed_mark.fill.actual_fill_price_raw,
                observed_at=market.observed_at,
                execution_fill=self._exit_diagnostics(
                    position, refreshed_mark.fill, control, trace
                ),
            )
            self._logger.info("paper_exit_latency", mint=position.mint, **trace)
        if llm_reason is not None and result.fill is not None:
            from memebot.models.paper import PaperExecutionEvidence

            result = result.model_copy(
                update={
                    "fill": result.fill.model_copy(
                        update={
                            "evidence": (
                                *result.fill.evidence,
                                PaperExecutionEvidence(
                                    code="ollama_reason",
                                    value=llm_reason,
                                    message="Local model paper exit rationale",
                                ),
                            ),
                        }
                    ),
                }
            )
        completed = (
            _paper_monitor_event(
                position=position,
                portfolio=portfolio,
                market=market,
                result=result,
                exit_reason=intent.reason,
            )
            if event is None
            else _paper_event(
                trigger_event=event,
                portfolio=portfolio,
                market=market,
                result=result,
                strategy_key=position.strategy_key,
                decision_event_id=None,
                kind=f"exit:{position.position_id}:{intent.reason}",
            )
        )
        await self._publish(completed)
        if result.status == PaperOrderStatus.FILLED and intent.effect == PositionEffect.CLOSE:
            self._hazard_since.pop(position.mint, None)

    async def _execute_pending_manual_close(self, event: TokenTrade) -> bool:
        action = await self._pending.pending_for_mint(event.mint, action="manual_close")
        if action is None:
            return False
        portfolio = await self._registry.active_paper_portfolio()
        position = await self._registry.open_position(event.mint)
        if portfolio is None or portfolio.portfolio_id != action.portfolio_id or position is None:
            await self._pending.finish(
                action.id,
                status="cancelled",
                reason="position_no_longer_open",
            )
            return True
        market = await self._registry.paper_market_context(event.mint, as_of=utc_now())
        if market is None or market.quote_asset != WRAPPED_SOL_MINT:
            return True
        market = await self._refresh_market(market, for_exit=True)
        try:
            quote = await self._quote_prices.quote_price(portfolio.currency)
        except QuotePriceError:
            return True
        decision_at = utc_now()
        await self._execution_delay()
        market = await self._refresh_market(market, for_exit=True)
        result = self._simulator.simulate_sell(
            market,
            quote,
            token_amount_raw=position.token_quantity_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="manual_paper_sell_on_fresh_trade",
            signal_at=event.source_event_at,
            decision_at=decision_at,
            executed_at=utc_now(),
        )
        if result.rejection_reason == "market_snapshot_stale":
            return True
        completed = _paper_event(
            trigger_event=event,
            portfolio=portfolio,
            market=market,
            result=result,
            strategy_key=position.strategy_key,
            decision_event_id=None,
            kind=f"pending_manual_close:{action.id}",
        )
        await self._publish(completed)
        await self._pending.finish(
            action.id,
            status="completed" if result.status == PaperOrderStatus.FILLED else "cancelled",
            reason=result.rejection_reason or "filled_on_fresh_trade",
            completion_event_id=completed.event_id,
        )
        return True

    async def monitor_open_positions(self) -> None:
        """The timer and stream share one exit policy and execution-time checks."""
        if not self._settings.paper_trading_enabled:
            return
        positions = await self._registry.open_positions()
        active = {position.mint for position in positions}
        for mint in list(self._position_locks):
            if (
                mint not in active
                and mint not in self._exit_tasks
                and not self._position_locks[mint].locked()
            ):
                self._position_locks.pop(mint)
        results = await asyncio.gather(
            *(
                self._protect_position(position)
                for position in positions
                if not self._position_locks.get(position.mint, asyncio.Lock()).locked()
            ),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                self._logger.error("exit_recovery_attempt_failed", error_type=type(result).__name__)

    async def queue_position_watchdog(self) -> None:
        """A slow bank on one mint must not postpone the next watchdog of another."""
        if not self._settings.paper_trading_enabled:
            return
        positions = await self._registry.open_positions()
        active = {position.mint for position in positions}
        for mint in list(self._position_locks):
            if mint not in active and mint not in self._exit_tasks:
                if not self._position_locks[mint].locked():
                    self._position_locks.pop(mint)
        for position in positions:
            if (
                position.mint not in self._exit_tasks
                and not self._position_locks.get(position.mint, asyncio.Lock()).locked()
            ):
                self.wake_open_position(position.mint, None, utc_now())

    async def _record_exit_recovery(
        self,
        position: PositionSnapshot,
        portfolio: PortfolioSnapshot,
        market: ExecutionMarketSnapshot,
        reason: str,
    ) -> None:
        await self._publish(
            _paper_monitor_event(
                position=position,
                portfolio=portfolio,
                market=market,
                result=_rejection(PaperOrderSide.SELL, position.remaining_cost_basis, reason),
                exit_reason="exit_recovery",
            )
        )

    async def _cancel_pending(self, action: PendingPaperAction | None, reason: str) -> None:
        if action is not None:
            await self._pending.finish(action.id, status="cancelled", reason=reason)

    async def _pause_if_daily_loss_limit_reached(self, as_of: datetime) -> None:
        if await self._risk_governor.daily_loss_limit_reached(as_of=as_of):
            await self._pause_for_daily_loss_limit()

    async def _pause_for_daily_loss_limit(self) -> None:
        _control, changed = await self._controls.pause_automatically()
        if changed:
            self._logger.error("paper_entries_paused_daily_loss_limit")

    async def _refresh_market(
        self, market: ExecutionMarketSnapshot, *, for_exit: bool = False
    ) -> ExecutionMarketSnapshot:
        refresher = self._exit_market_refresher if for_exit else self._market_refresher
        if refresher is None:
            return market
        refreshed = await refresher.refresh(market)
        if refreshed.price_source_disagreement_pct is not None:
            self._logger.warning(
                "price_source_comparison",
                mint=market.mint,
                for_exit=for_exit,
                **price_metadata(refreshed, utc_now()),
            )
        return refreshed

    async def _execution_delay(self) -> None:
        """No position exists during submission; fills use state after this delay."""
        await asyncio.sleep(
            (self._settings.paper_compute_latency_ms + self._settings.paper_submission_latency_ms)
            / 1000
        )

    def _position_size(
        self,
        portfolio: PortfolioSnapshot,
        score: Decimal,
        strategy_key: str,
        control: TradingControlSnapshot,
    ) -> Decimal:
        # Adaptive sizing searches down from the cap using executable liquidity
        # and costs. An uncalibrated score never amplifies the allocation.
        del score, strategy_key
        capital = min(portfolio.initial_cash, portfolio.initial_cash + portfolio.realized_pnl)
        allocation = min(
            control.max_position_percent
            if self._settings.paper_adaptive_position_sizing
            else control.base_position_percent,
            control.max_position_percent,
            self._settings.paper_risk_per_trade_percent
            * 100
            / max(control.stop_loss_percent, self._settings.paper_stop_loss_risk_reserve_percent),
        )
        target = max(Decimal(0), capital) * allocation / Decimal(100)
        return min(target, portfolio.cash_balance).quantize(Decimal("0.00000001"))

    def _sol_tier_size(
        self,
        portfolio: PortfolioSnapshot,
        score: Decimal,
        sol_price: Decimal,
        control: TradingControlSnapshot,
    ) -> Decimal:
        """Small / medium / large SOL size by strategy score (paper_sizing_mode).

        Telegram-set tiers win; otherwise .env sizes, with the whole portfolio on top.
        """
        # Keep a little cash for fees so a full-portfolio buy is not rejected for them.
        available = portfolio.cash_balance * Decimal("0.97")
        small = control.sol_tier_small or self._settings.paper_sol_tier_small
        medium = control.sol_tier_medium or self._settings.paper_sol_tier_medium
        if score >= self._settings.paper_sol_tier_full_score:
            large = control.sol_tier_large
            target = available if large is None else large * sol_price
        elif score >= self._settings.paper_sol_tier_medium_score:
            target = medium * sol_price
        else:
            target = small * sol_price
        return max(Decimal(0), min(target, available)).quantize(Decimal("0.00000001"))

    def _liquidity_adjusted_buy(
        self,
        *,
        portfolio: PortfolioSnapshot,
        control: TradingControlSnapshot,
        strategy_key: str,
        target: Decimal,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        signal_at: datetime,
        decision_at: datetime,
        executed_at: datetime | None = None,
        available_budget: Decimal | None = None,
    ) -> tuple[Decimal, PaperOrderResult]:
        minimum = max(
            self._settings.paper_min_order_amount,
            portfolio.initial_cash * self._settings.paper_min_position_percent / Decimal(100),
        ).quantize(Decimal("0.00000001"))
        budget = min(
            portfolio.cash_balance,
            available_budget if available_budget is not None else portfolio.cash_balance,
        )
        fixed_fee = (
            self._settings.paper_network_fee_sol + self._settings.paper_priority_fee_sol
        ) * quote_price.price
        affordable = max(
            Decimal(0),
            (budget - fixed_fee) / (1 + self._settings.paper_execution_provider_fee_bps / 10000),
        )
        requested = min(target, affordable).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        if requested < minimum:
            return requested, _rejection(
                PaperOrderSide.BUY,
                max(requested, Decimal("0.00000001")),
                "minimum_order_not_affordable_within_limits",
            )
        while True:
            result = self._simulator.simulate_buy(
                market,
                quote_price,
                requested_portfolio_amount=requested,
                signal_at=signal_at,
                decision_at=decision_at,
                executed_at=executed_at,
            )
            if result.fill is None:
                if (
                    result.rejection_reason
                    in {"insufficient_real_token_reserves", "insufficient_real_quote_reserves"}
                    and requested > minimum
                ):
                    requested = max(minimum, requested * Decimal("0.80")).quantize(
                        Decimal("0.00000001"), rounding=ROUND_DOWN
                    )
                    continue
                return requested, result
            impact_too_high = result.fill.price_impact_bps > self._maximum_entry_price_impact_bps(
                strategy_key
            )
            round_trip_cost = self._estimated_round_trip_cost_bps(
                result, market, quote_price, executed_at or decision_at
            )
            round_trip_too_high = (
                round_trip_cost is None
                or round_trip_cost > self._maximum_round_trip_cost_bps(strategy_key)
            )
            if not impact_too_high and not round_trip_too_high:
                from memebot.models.paper import PaperExecutionEvidence

                assert round_trip_cost is not None
                loss_fraction = round_trip_cost / Decimal(10000)
                # Linear-proceeds reference only; actual pool repricing is nonlinear.
                break_even = (
                    loss_fraction / (1 - loss_fraction) * 100 if loss_fraction < 1 else None
                )
                result = result.model_copy(
                    update={
                        "fill": result.fill.model_copy(
                            update={
                                "evidence": (
                                    *result.fill.evidence,
                                    PaperExecutionEvidence(
                                        code="estimated_round_trip_cost_bps",
                                        value=round_trip_cost,
                                        message="Reserve liquidation with both-side modeled costs",
                                    ),
                                    PaperExecutionEvidence(
                                        code="linear_proceeds_break_even_percent",
                                        value=break_even,
                                        message="Cost hurdle; assumes linear exit proceeds",
                                    ),
                                ),
                            }
                        )
                    }
                )
                return requested, result
            if requested <= minimum:
                reason = (
                    "entry_price_impact_above_strategy_limit"
                    if impact_too_high
                    else "round_trip_cost_above_strategy_limit"
                )
                return requested, _rejection(PaperOrderSide.BUY, requested, reason)
            requested = max(minimum, requested * Decimal("0.80")).quantize(Decimal("0.00000001"))

    @staticmethod
    def _entry_cash_cost(result: PaperOrderResult) -> Decimal:
        assert result.fill is not None
        fill = result.fill
        return (
            fill.gross_portfolio_amount
            + (fill.network_fee_quote_raw + fill.execution_provider_fee_quote_raw)
            / Decimal(1_000_000_000)
            * fill.quote_price_in_portfolio_currency
        )

    def _estimated_round_trip_cost_bps(
        self,
        buy: PaperOrderResult,
        market: ExecutionMarketSnapshot,
        quote_price: QuotePrice,
        decision_at: datetime,
    ) -> Decimal | None:
        if buy.fill is None:
            return None
        liquidation = self._simulator.simulate_sell(
            market,
            quote_price,
            token_amount_raw=buy.fill.token_amount_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="entry_cost_probe",
            signal_at=decision_at,
            decision_at=decision_at,
        )
        if liquidation.fill is None:
            return None
        network_fee = (
            buy.fill.network_fee_quote_raw
            / Decimal(1_000_000_000)
            * buy.fill.quote_price_in_portfolio_currency
        )
        provider_fee = (
            buy.fill.execution_provider_fee_quote_raw
            / Decimal(1_000_000_000)
            * buy.fill.quote_price_in_portfolio_currency
        )
        entry_cost = buy.fill.gross_portfolio_amount + network_fee + provider_fee
        exit_proceeds = (
            liquidation.fill.gross_portfolio_amount - liquidation.fill.total_fee_portfolio
        )
        if entry_cost <= 0:
            return None
        return max(Decimal(0), (entry_cost - exit_proceeds) / entry_cost * Decimal(10_000))

    def _maximum_entry_price_impact_bps(self, strategy_key: str) -> Decimal:
        if strategy_key == "conservative":
            return self._settings.paper_max_entry_price_impact_bps_conservative
        if strategy_key == "aggressive":
            return self._settings.paper_max_entry_price_impact_bps_aggressive
        return self._settings.paper_max_entry_price_impact_bps_balanced

    def _maximum_round_trip_cost_bps(self, strategy_key: str) -> Decimal:
        if strategy_key == "conservative":
            return self._settings.paper_max_round_trip_cost_bps_conservative
        if strategy_key == "aggressive":
            return self._settings.paper_max_round_trip_cost_bps_aggressive
        return self._settings.paper_max_round_trip_cost_bps_balanced

    def _is_stagnant(
        self, holding_seconds: float, peak_return: Decimal, current_return: Decimal
    ) -> bool:
        return (
            holding_seconds >= self._settings.paper_stagnation_exit_seconds
            and peak_return < self._settings.paper_stagnation_min_mfe_percent
            and current_return <= 0
        )

    async def _publish_rejection(
        self,
        event: StrategyDecisionCreated,
        portfolio: PortfolioSnapshot,
        market: ExecutionMarketSnapshot | None,
        reason: str,
    ) -> None:
        requested = max(
            Decimal("0.00000001"),
            portfolio.initial_cash * self._settings.paper_base_position_percent / Decimal(100),
        )
        await self._publish(
            _paper_event(
                trigger_event=event,
                portfolio=portfolio,
                market=market,
                result=_rejection(PaperOrderSide.BUY, requested, reason),
                strategy_key=event.strategy_key,
                decision_event_id=event.event_id,
                kind="entry",
            )
        )

    async def close(self) -> None:
        self._closed_for_exits = True
        for task in list(self._exit_tasks.values()):
            task.cancel()
        await asyncio.gather(*self._exit_tasks.values(), return_exceptions=True)
        await self._quote_prices.close()


def _paper_event(
    *,
    trigger_event: StrategyDecisionCreated | TokenTrade,
    portfolio: PortfolioSnapshot,
    market: ExecutionMarketSnapshot | None,
    result: PaperOrderResult,
    strategy_key: str,
    decision_event_id: UUID | None,
    kind: str,
) -> PaperOrderCompleted:
    completed_at = result.fill.filled_at if result.fill is not None else utc_now()
    result = with_price_evidence(result, market, completed_at)
    return PaperOrderCompleted(
        event_id=uuid5(
            _PAPER_EVENT_NAMESPACE,
            f"{portfolio.portfolio_id}:{trigger_event.event_id}:{kind}",
        ),
        provider="bullseye_paper_engine",
        source_event_at=completed_at,
        correlation_id=trigger_event.correlation_id or trigger_event.event_id,
        source_slot=market.source_slot if market is not None else trigger_event.source_slot,
        portfolio_id=portfolio.portfolio_id,
        mint=trigger_event.mint,
        trigger_event_id=trigger_event.event_id,
        decision_event_id=decision_event_id,
        strategy_key=strategy_key,
        market=market.market if market is not None else None,
        venue=market.venue if market is not None else LaunchVenue.UNKNOWN,
        lifecycle=market.lifecycle if market is not None else MarketLifecycle.UNKNOWN,
        result=result,
    )


def _rejection(side: PaperOrderSide, requested: Decimal, reason: str) -> PaperOrderResult:
    return PaperOrderResult(
        status=PaperOrderStatus.REJECTED,
        side=side,
        position_effect=PositionEffect.NONE,
        requested_portfolio_amount=max(requested, Decimal("0.00000001")),
        rejection_reason=reason,
    )


def _paper_monitor_event(
    *,
    position: PositionSnapshot,
    portfolio: PortfolioSnapshot,
    market: ExecutionMarketSnapshot,
    result: PaperOrderResult,
    exit_reason: str,
) -> PaperOrderCompleted:
    trigger_id = uuid5(
        _PAPER_EVENT_NAMESPACE,
        f"monitor:{position.position_id}:{market.source_slot}:{exit_reason}:{utc_now().isoformat()}",
    )
    completed_at = result.fill.filled_at if result.fill is not None else utc_now()
    result = with_price_evidence(result, market, completed_at)
    return PaperOrderCompleted(
        event_id=uuid5(_PAPER_EVENT_NAMESPACE, f"{trigger_id}:completed"),
        provider="bullseye_paper_position_monitor",
        source_event_at=completed_at,
        correlation_id=trigger_id,
        source_slot=market.source_slot,
        portfolio_id=portfolio.portfolio_id,
        mint=position.mint,
        trigger_event_id=trigger_id,
        decision_event_id=None,
        strategy_key=position.strategy_key,
        market=market.market,
        venue=market.venue,
        lifecycle=market.lifecycle,
        result=result,
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
