from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.core.instance import instance_lock
from memebot.core.logging import get_logger
from memebot.core.metrics import EventMetrics
from memebot.core.sampling import sampled_mint
from memebot.eligibility import paper_candidate_rejection, research_rejection
from memebot.events.bus import EventBus
from memebot.events.models import (
    DomainEvent,
    MarketFeatureSnapshotCreated,
    PaperActionExpired,
    PaperActionPending,
    PaperOrderCompleted,
    ProviderHealthUpdated,
    StrategyDecisionCreated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenRiskAssessed,
    TokenTrade,
)
from memebot.intelligence.alpha_filter import AlphaFilterService
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.intelligence.ollama_policy import OllamaPaperPolicy
from memebot.intelligence.risk.collector import SolanaRiskCollector
from memebot.intelligence.risk.coordinator import RiskAssessmentCoordinator
from memebot.intelligence.risk.rules import RiskAssessor, RiskPolicy
from memebot.intelligence.wallet_projection import DurableWalletProjector
from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.models.strategy import ScoreResult, StrategyDecisionAction
from memebot.paper.engine import PaperTradingEngine
from memebot.paper.market_refresh import (
    CurrentPaperMarketRefresher,
    FallbackMarketSnapshotRefresher,
)
from memebot.providers.birdeye.client import BirdeyeClient
from memebot.providers.curve_calibration import calibrate_curve
from memebot.providers.price.coingecko import CoinGeckoQuotePriceProvider
from memebot.providers.pumpportal import PumpPortalDiscoveryProvider
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.evidence_stream import TransactionEvidence
from memebot.providers.solana.operational_evidence import OperationalEvidenceCache
from memebot.providers.solana.pump import PumpDiscoveryProvider
from memebot.providers.solana.rpc import FallbackSolanaRpcProvider, JsonRpcSolanaClient
from memebot.providers.solana.stream_budget import RollingStreamBudget
from memebot.pulse.service import PulseService
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.pending import PendingPaperActionRepository
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.wallets import WalletIntelligenceRepository
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.runner import MultiStrategyRunner
from memebot.telegram.notifications import (
    TelegramTradeNotifier,
    tracked_wallet_notification,
)


async def run_database_check(settings: Settings) -> None:
    """Validate database wiring without starting the market-data loop."""
    logger = get_logger("memebot.worker")
    database = Database(create_database_engine(settings.database_url, echo=settings.database_echo))
    try:
        await database.healthcheck()
        logger.info(
            "worker_database_ready",
            execution_mode=settings.execution_mode,
            network=settings.network,
            enabled_providers=sorted(settings.enabled_providers),
        )
    finally:
        await database.dispose()


async def run_discovery_worker(
    settings: Settings,
    *,
    run_seconds: float | None = None,
    on_ready: Callable[[], Awaitable[None]] | None = None,
) -> None:
    with instance_lock("discover"):
        await _run_discovery_worker(settings, run_seconds=run_seconds, on_ready=on_ready)


async def _run_discovery_worker(
    settings: Settings,
    *,
    run_seconds: float | None = None,
    on_ready: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """Run the Phase 1 read-only Pump/PumpSwap discovery worker."""
    logger = get_logger("memebot.discovery")
    runtime_summary = settings.safe_summary()
    database = Database(create_database_engine(settings.database_url, echo=settings.database_echo))
    rpc = JsonRpcSolanaClient(
        str(settings.solana_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    exit_rpc = JsonRpcSolanaClient(
        str(settings.solana_exit_rpc_http_url),
        timeout_seconds=settings.solana_rpc_timeout_seconds,
    )
    risk_rpc = FallbackSolanaRpcProvider(rpc, exit_rpc)
    provider = (
        PumpPortalDiscoveryProvider(
            settings,
            calibrate=lambda mint, curve, signature: calibrate_curve(
                risk_rpc, mint, curve, signature
            ),
        )
        if settings.pumpportal_api_key is not None
        else PumpDiscoveryProvider(settings, rpc)
    )
    executed_cache = None
    rpc_endpoint = urlsplit(str(settings.solana_rpc_http_url))
    if (
        isinstance(provider, PumpDiscoveryProvider)
        and settings.solana_executed_stream_enabled
        and rpc_endpoint.hostname == "solana-mainnet.g.alchemy.com"
    ):
        executed_cache = OperationalEvidenceCache(
            rpc_endpoint.path.rsplit("/", 1)[-1],
            max_bytes=settings.solana_executed_stream_session_bytes,
            error_directory=Path("analysis/operational_packet_errors"),
            budget=RollingStreamBudget(
                Path("analysis/runtime/executed_stream_budget.json"),
                settings.solana_executed_stream_hourly_bytes,
            )
            if settings.solana_executed_stream_hourly_bytes
            else None,
        )
        provider.transaction_evidence_lookup = executed_cache.lookup
    outcome_recorder = OutcomeRecorder(database.sessions)
    registry = TokenRegistry(
        database.sessions,
        max_mark_age_seconds=settings.paper_max_market_staleness_seconds,
        outcome_recorder=outcome_recorder,
    )
    alpha_filter = AlphaFilterService(
        settings,
        registry,
        (
            BirdeyeClient(
                str(settings.birdeye_base_url),
                settings.birdeye_api_key,
                timeout_seconds=settings.birdeye_timeout_seconds,
                minimum_interval_seconds=settings.birdeye_minimum_interval_seconds,
            )
            if settings.birdeye_api_key is not None
            else None
        ),
    )
    pending_paper_actions = PendingPaperActionRepository(database.sessions)
    wallet_intelligence = WalletIntelligenceRepository(
        database.sessions,
        early_entry_seconds=settings.wallet_early_entry_seconds,
        candidate_min_launches=settings.wallet_candidate_min_launches,
        scored_min_launches=settings.wallet_scored_min_launches,
        high_confidence_min_launches=settings.wallet_high_confidence_min_launches,
        success_expansion_percent=settings.wallet_success_expansion_percent,
    )
    controls = ControlRepository(database.sessions)
    experiments = ExperimentRepository(database.sessions)
    telegram_notifier = _telegram_notifier(settings, registry)
    feature_engine = RollingFeatureEngine(
        settings.feature_windows_seconds,
        snapshot_interval_seconds=settings.feature_snapshot_interval_seconds,
        max_lateness_seconds=settings.feature_max_lateness_seconds,
        state_tracker=provider.state_tracker
        if isinstance(provider, PumpDiscoveryProvider)
        else None,
    )
    if isinstance(provider, PumpDiscoveryProvider):
        provider.on_price_gap = feature_engine.invalidate_price_history
    bus = EventBus()
    strategy_configurations = initial_strategy_presets()
    strategy_runner = MultiStrategyRunner(strategy_configurations)
    ollama_policy = (
        OllamaPaperPolicy(
            str(settings.ollama_base_url),
            settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            venue_fee_bps=settings.paper_venue_fee_bps,
            execution_provider_fee_bps=settings.paper_execution_provider_fee_bps,
            latency_slippage_bps=settings.paper_latency_slippage_bps,
        )
        if settings.ollama_model
        else None
    )
    active_strategy_configuration = next(
        item for item in strategy_configurations if item.active_for_execution
    )
    quote_prices = CoinGeckoQuotePriceProvider(str(settings.coingecko_base_url))
    pulse = (
        PulseService(database.sessions, settings, quote_prices) if settings.pulse_enabled else None
    )
    paper_engine = PaperTradingEngine(
        settings,
        registry,
        controls,
        pending_paper_actions,
        quote_prices,
        bus.publish,
        entry_thresholds={item.key: item.score_threshold for item in strategy_configurations},
        pulse=pulse,
        exit_market_refresher=FallbackMarketSnapshotRefresher(
            CurrentPaperMarketRefresher(exit_rpc, for_exit=True),
            CurrentPaperMarketRefresher(rpc, for_exit=True),
        ),
        market_refresher=CurrentPaperMarketRefresher(rpc),
        ollama_policy=ollama_policy,
    )
    if isinstance(provider, PumpDiscoveryProvider):
        provider.set_exit_wakeup(paper_engine.wake_open_position)
    risk_coordinator = RiskAssessmentCoordinator(
        registry,
        SolanaRiskCollector(
            risk_rpc,
            commitment=settings.solana_commitment,
            retry_count=settings.solana_account_retry_count,
            retry_delay_seconds=settings.solana_account_retry_delay_seconds,
        ),
        RiskAssessor(RiskPolicy.from_settings(settings)),
        bus.publish,
        worker_count=settings.risk_assessment_workers,
        queue_size=settings.risk_assessment_queue_size,
        reassessment_interval_seconds=settings.risk_reassessment_interval_seconds,
        max_assessments_per_hour=settings.risk_assessment_max_per_hour,
        max_assessments_per_day=settings.risk_assessment_max_per_day,
        market_refresher=CurrentPaperMarketRefresher(
            rpc,
            state_tracker=provider.state_tracker
            if isinstance(provider, PumpDiscoveryProvider)
            else None,
        ),
    )
    prefilter_rejection_reasons: dict[str, tuple[str, ...]] = {}
    paper_trade_queue: dict[str, tuple[TokenTrade, MarketFeatureSnapshotCreated | None]] = {}
    paper_trade_ready = asyncio.Event()
    metrics = EventMetrics()

    async def process_event(event: DomainEvent) -> None:
        inserted = await registry.handle(event)
        if not inserted:
            return
        if executed_cache is not None:
            executed_cache.observe(event)
            if isinstance(provider, PumpDiscoveryProvider):
                for mint in executed_cache.watch.markets:
                    provider.market_notification_locks.setdefault(mint, asyncio.Lock())
                for mint, lock in list(provider.market_notification_locks.items()):
                    if mint not in executed_cache.watch.markets and not lock.locked():
                        provider.market_notification_locks.pop(mint, None)
        metrics.observe(event, utc_now())
        if (
            isinstance(event, TokenTrade)
            and event.normalized_state.continuity_status == "SLOT_REGRESSION"
        ):
            # Retain the raw observation, but a rejected historical sample must
            # not replace the newer rolling signal or trigger entry/exit work.
            return
        if isinstance(event, TokenTrade) or (
            isinstance(event, TokenLifecycleChanged)
            and event.lifecycle
            in {
                MarketLifecycle.GRADUATION,
                MarketLifecycle.POST_GRADUATION,
                MarketLifecycle.DEAD_OR_ILLIQUID,
            }
        ):
            wallet_projector.wake()
        if inserted and isinstance(event, TokenDiscovered):
            logger.info(
                "token_discovered",
                mint=event.mint,
                symbol=event.symbol,
                launch_venue=event.launch_venue.value,
                source_slot=event.source_slot,
            )
        elif inserted and isinstance(event, ProviderHealthUpdated):
            if event.state.value in {"degraded", "disconnected"}:
                feature_engine.invalidate_price_history()
            logger.info(
                "provider_health",
                provider=event.provider,
                state=event.state.value,
                reconnect_count=event.reconnect_count,
                error_code=event.error_code,
            )
            if telegram_notifier is not None:
                telegram_notifier.enqueue_event(event)
            if event.error_code == "rpc_service_halted":
                _control, changed = await controls.pause_for_provider_halt()
                if changed:
                    logger.error(
                        "paper_entries_paused_provider_halt",
                        provider=event.provider,
                    )
        elif isinstance(event, TokenRiskAssessed):
            logger.info(
                "token_risk_assessed",
                mint=event.mint,
                allowed=event.result.allowed,
                risk_score=(
                    str(event.result.risk_score) if event.result.risk_score is not None else None
                ),
                hard_reject_reasons=event.result.hard_reject_reasons,
                critical_unknowns=event.result.critical_unknowns,
            )
            feature, token_created_at = await registry.strategy_context(
                event.mint, as_of=event.source_event_at
            )
            control = await controls.get()
            for decision in strategy_runner.evaluate(
                event,
                feature,
                token_created_at=token_created_at,
                active_strategy_key=(control.active_strategy_key if control is not None else None),
            ):
                if (
                    ollama_policy is not None
                    and decision.active_strategy
                    and decision.action == StrategyDecisionAction.ENTER_CANDIDATE
                ):
                    try:
                        choice = await ollama_policy.entry(
                            event, feature, await registry.active_paper_portfolio()
                        )
                        decision = decision.model_copy(
                            update={
                                "provider": "bullseye_ollama_policy",
                                "action": (
                                    StrategyDecisionAction.ENTER_CANDIDATE
                                    if choice.action == "buy"
                                    else StrategyDecisionAction.SKIP
                                ),
                                "score": ScoreResult(
                                    final_score=choice.confidence,
                                    component_completeness_percent=event.result.data_completeness_percent,
                                    components=(),
                                ),
                                "reasons": (
                                    f"ollama_model:{ollama_policy.model}",
                                    f"llm:{choice.reason}",
                                ),
                                "requested_position_percent": (
                                    choice.allocation_percent if choice.action == "buy" else None
                                ),
                            }
                        )
                    except Exception as exc:
                        logger.warning(
                            "ollama_entry_unavailable",
                            mint=event.mint,
                            error_type=type(exc).__name__,
                            detail=str(exc)[:160],
                        )
                        decision = decision.model_copy(
                            update={
                                "provider": "bullseye_ollama_policy",
                                "action": StrategyDecisionAction.SKIP,
                                "reasons": ("ollama_unavailable_no_entry",),
                            }
                        )
                await bus.publish(decision)
        elif isinstance(event, StrategyDecisionCreated):
            if event.active_strategy and event.action.value == "enter_candidate":
                if not rpc.available:
                    await controls.pause_automatically()
                    logger.error("paper_entries_paused_rpc_circuit_open")
                if not experiment_matches(
                    await experiments.active(), runtime_summary, await controls.get()
                ):
                    await controls.pause_automatically()
                    logger.error("paper_entries_paused_experiment_drift")
            if (
                isinstance(provider, PumpPortalDiscoveryProvider)
                and event.active_strategy
                and event.action.value != "enter_candidate"
                and research_rejection(event.price_evidence) is None
                and sampled_mint(event.mint, settings.research_control_sample_percent)
            ):
                await provider.observe_research(event.mint)
            logger.info(
                "strategy_decision_created",
                mint=event.mint,
                strategy=event.strategy_key,
                active_strategy=event.active_strategy,
                action=event.action.value,
                regime=event.regime.value,
                final_score=(
                    str(event.score.final_score) if event.score.final_score is not None else None
                ),
                reasons=event.reasons,
            )
            candidate_requires_blocking_alpha = (
                event.active_strategy
                and event.action.value == "enter_candidate"
                and settings.alpha_filter_enabled
                and not settings.alpha_filter_shadow_mode
            )
            if candidate_requires_blocking_alpha:
                alpha_snapshot = await alpha_filter.assess(event)
                if alpha_snapshot is not None:
                    logger.info(
                        "alpha_filter_assessed",
                        mint=event.mint,
                        market_regime=alpha_snapshot.market_regime,
                        shadow_reasons=alpha_snapshot.shadow_reasons,
                        blocking_reasons=alpha_snapshot.blocking_reasons,
                    )
            if telegram_notifier is not None:
                telegram_notifier.enqueue_event(event)
            await paper_engine.on_decision(event)
            if (
                event.active_strategy
                and event.action.value == "enter_candidate"
                and not candidate_requires_blocking_alpha
            ):
                alpha_snapshot = await alpha_filter.assess(event)
                if alpha_snapshot is not None:
                    logger.info(
                        "alpha_filter_shadow_assessed_after_execution",
                        mint=event.mint,
                        market_regime=alpha_snapshot.market_regime,
                        shadow_reasons=alpha_snapshot.shadow_reasons,
                    )
        elif isinstance(event, PaperOrderCompleted):
            if event.result.fill is not None:
                if event.result.position_effect.value == "open":
                    feature_engine.pin_mint(event.mint)
                elif event.result.position_effect.value == "close":
                    feature_engine.unpin_mint(event.mint)
            logger.info(
                "paper_order_completed",
                portfolio_id=str(event.portfolio_id),
                mint=event.mint,
                strategy=event.strategy_key,
                side=event.result.side.value,
                status=event.result.status.value,
                position_effect=event.result.position_effect.value,
                rejection_reason=event.result.rejection_reason,
                exit_reason=event.result.exit_reason,
            )
            if (
                isinstance(provider, (PumpPortalDiscoveryProvider, PumpDiscoveryProvider))
                and event.result.status.value == "filled"
            ):
                if (
                    event.result.side.value == "buy"
                    and event.result.position_effect.value == "open"
                ):
                    await provider.pin_open_position(event.mint)
                elif (
                    event.result.side.value == "sell"
                    and event.result.position_effect.value == "close"
                ):
                    await provider.unpin_closed_position(event.mint)
            if telegram_notifier is not None:
                telegram_notifier.enqueue_event(event)
        elif isinstance(event, PaperActionPending):
            logger.info(
                "paper_action_pending",
                mint=event.mint,
                action=event.action,
                expires_at=event.expires_at.isoformat(),
                reason=event.reason,
            )
            if telegram_notifier is not None:
                telegram_notifier.enqueue_event(event)
        elif isinstance(event, PaperActionExpired):
            logger.warning(
                "paper_action_expired",
                mint=event.mint,
                action=event.action,
                reason=event.reason,
            )
            if telegram_notifier is not None:
                telegram_notifier.enqueue_event(event)
        snapshot = None
        if isinstance(event, TokenTrade):
            snapshot = feature_engine.ingest_trade(event)
            prefilter_passes, rejection_reasons, prefilter_window = _risk_prefilter_evaluation(
                settings, snapshot
            )
            scope_block = paper_candidate_rejection(event.normalized_state.evidence())
            if scope_block:
                logger.debug("entry_universe_rejected", mint=event.mint, reason=scope_block)
            if prefilter_passes and scope_block is None:
                prefilter_rejection_reasons.pop(event.mint, None)
                if not risk_coordinator.enqueue(event):
                    logger.warning("risk_assessment_queue_full", mint=event.mint)
            elif (
                prefilter_window is not None
                and prefilter_window.trade_count >= settings.risk_prefilter_min_trades
                and prefilter_rejection_reasons.get(event.mint) != rejection_reasons
            ):
                prefilter_rejection_reasons[event.mint] = rejection_reasons
                logger.info(
                    "risk_prefilter_rejected",
                    mint=event.mint,
                    reasons=rejection_reasons,
                    trade_count=prefilter_window.trade_count,
                    unique_buyers=prefilter_window.unique_buyers,
                    flow_imbalance=(
                        str(prefilter_window.flow_imbalance)
                        if prefilter_window.flow_imbalance is not None
                        else None
                    ),
                    window_seconds=prefilter_window.window_seconds,
                )
            # Persist every market trade, but coalesce execution work by mint so
            # RPC/submission delays never block the websocket reader.
            if settings.paper_trading_enabled:
                paper_trade_queue[event.mint] = (
                    event,
                    snapshot
                    or (
                        feature_engine.current_snapshot(event)
                        if feature_engine.has_open_position(event.mint)
                        else None
                    ),
                )
                if len(paper_trade_queue) > 256:
                    paper_trade_queue.pop(next(iter(paper_trade_queue)))
                    logger.warning("paper_execution_queue_coalesced")
                paper_trade_ready.set()
        elif isinstance(event, TokenLifecycleChanged):
            snapshot = feature_engine.ingest_lifecycle(event)
            if (
                event.lifecycle
                in {
                    MarketLifecycle.FINAL_STRETCH,
                    MarketLifecycle.GRADUATION,
                }
                and not event.entry_rejection_reason
                and event.is_mayhem_mode is False
                and not risk_coordinator.enqueue(event)
            ):
                logger.warning("risk_assessment_queue_full", mint=event.mint)
        if snapshot is not None:
            await bus.publish(snapshot)

    bus.subscribe(DomainEvent, process_event)
    if executed_cache is not None and isinstance(provider, PumpDiscoveryProvider):
        native_provider = provider
        packet_cache = executed_cache

        async def publish_executed_packet(packet: TransactionEvidence) -> None:
            message: dict[str, object] = {
                "method": "logsNotification",
                "params": {
                    "result": {
                        "context": {"slot": packet.slot},
                        "value": {
                            "signature": packet.signature,
                            "err": None,
                            "logs": packet.transaction["meta"]["logMessages"],
                        },
                    }
                },
            }
            native_provider._wake_received_positions(message, packet.received_at)
            await native_provider._handle_notification(
                message,
                bus.publish,
                received_at=packet.received_at,
                transaction_evidence=packet.transaction,
            )

        async def publish_deferred_native(
            message: dict[str, object], received_at: datetime
        ) -> None:
            await native_provider._handle_notification(
                message, bus.publish, received_at=received_at, allow_defer=False
            )

        def executed_gap(reason: str) -> None:
            for mint in packet_cache.watch.markets:
                native_provider.state_tracker.invalidate(curve_address(mint), reason)
                feature_engine.invalidate_price_history(mint)

        executed_cache.process_packet = publish_executed_packet
        executed_cache.on_gap = executed_gap
        executed_cache.process_native = publish_deferred_native
        native_provider.native_notification_router = executed_cache.defer_native
    pending_sweeper_task: asyncio.Task[None] | None = None
    wallet_backfill_task: asyncio.Task[int] | None = None
    wallet_projection_task: asyncio.Task[None] | None = None

    position_monitor_task: asyncio.Task[None] | None = None
    paper_trade_task: asyncio.Task[None] | None = None
    executed_cache_task: asyncio.Task[None] | None = None
    executed_watch_task: asyncio.Task[None] | None = None
    executed_processor_task: asyncio.Task[None] | None = None

    def wallet_activity_ready(activity: dict[str, Any]) -> None:
        if telegram_notifier is not None and settings.telegram_tracked_wallet_notifications_enabled:
            telegram_notifier.enqueue_text(tracked_wallet_notification(activity))

    async def project_wallet_batch() -> int:
        if isinstance(provider, PumpDiscoveryProvider) and provider.receive_backlogged:
            # No historical research starts while a received market packet waits.
            await asyncio.sleep(1)
            return 0
        processed = await wallet_intelligence.backfill_existing(
            limit=1, on_activity=wallet_activity_ready
        )
        reconciled = await wallet_intelligence.reconcile_terminal_lifecycles(limit=1)
        return processed + reconciled

    wallet_projector = DurableWalletProjector(
        project_wallet_batch,
        lambda error: logger.warning("wallet_projection_retry", error_code=type(error).__name__),
    )

    async def process_paper_trades() -> None:
        while True:
            await paper_trade_ready.wait()
            while paper_trade_queue:
                next_mint = next(
                    (mint for mint in paper_trade_queue if feature_engine.has_open_position(mint)),
                    next(iter(paper_trade_queue)),
                )
                event, feature = paper_trade_queue.pop(next_mint)
                try:
                    await paper_engine.on_trade(event, feature)
                except Exception:
                    logger.exception("paper_trade_processing_failed", mint=event.mint)
            paper_trade_ready.clear()

    async def sweep_pending_actions() -> None:
        while True:
            for action in await pending_paper_actions.expire_due():
                await bus.publish(
                    PaperActionExpired(
                        provider="bullseye_paper_engine",
                        source_event_at=utc_now(),
                        correlation_id=action.decision_event_id,
                        portfolio_id=action.portfolio_id,
                        mint=action.mint,
                        action=("entry" if action.action == "automatic_entry" else "manual_close"),
                        reason="fresh_market_timeout",
                        decision_event_id=action.decision_event_id,
                        requested_by_user_id=action.requested_by_user_id,
                    )
                )
            await asyncio.sleep(1)

    async def monitor_paper_positions() -> None:
        next_metrics_at = utc_now()
        while True:
            try:
                await paper_engine.queue_position_watchdog()
            except Exception:
                logger.exception("paper_position_monitor_failed")
            if utc_now() >= next_metrics_at:
                try:
                    logger.info(
                        "runtime_metrics",
                        metrics=metrics.snapshot(),
                        primary_rpc=rpc.metrics(),
                        exit_rpc=exit_rpc.metrics(),
                        feature_state_evictions=feature_engine.evicted_token_states,
                        native_instructions=(
                            dict(provider.native_instruction_metrics)
                            if isinstance(provider, PumpDiscoveryProvider)
                            else None
                        ),
                        executed_evidence=(
                            {
                                "cache": dict(executed_cache.metrics),
                                "status": executed_cache.status,
                                "native_pending": len(executed_cache.pending_native),
                                "reserved_hour_day_bytes": executed_cache.adapter.budget.usage()
                                if executed_cache.adapter.budget
                                else None,
                                "transport": dict(executed_cache.adapter.metrics),
                                "watched_markets": len(executed_cache.watch.markets),
                            }
                            if executed_cache is not None
                            else None
                        ),
                        portfolio=await registry.paper_portfolio_report(),
                    )
                except Exception:
                    logger.exception("runtime_metrics_collection_failed")
                next_metrics_at = utc_now() + timedelta(seconds=30)
            await asyncio.sleep(settings.paper_position_monitor_interval_seconds)

    try:
        await database.healthcheck()
        paper_trade_task = asyncio.create_task(process_paper_trades(), name="paper-trade-execution")
        await registry.ensure_strategy_configurations(strategy_configurations)
        await controls.ensure(
            active_strategy_key=active_strategy_configuration.key,
            base_position_percent=settings.paper_base_position_percent,
            max_position_percent=settings.paper_max_position_percent,
            max_open_positions=settings.paper_max_open_positions,
            stop_loss_percent=settings.paper_stop_loss_percent,
            take_profit_percent=settings.paper_take_profit_percent,
            trailing_stop_percent=settings.paper_trailing_stop_percent,
            max_holding_seconds=settings.paper_max_holding_seconds,
        )
        portfolio = await registry.ensure_default_paper_portfolio(
            initial_cash=settings.starting_capital,
            currency=settings.starting_capital_currency,
        )
        experiment = await experiments.active()
        experiment_matches_portfolio = (
            experiment is not None
            and experiment["portfolio_id"] == str(portfolio.portfolio_id)
            and experiment_matches(experiment, runtime_summary, await controls.get())
        )
        experiment_name = experiment["name"] if experiment is not None else None
        if not experiment_matches_portfolio:
            control = await controls.get()
            if control is not None and not control.entries_paused:
                await controls.set_paused(True, user_id=0)
            logger.warning(
                "paper_entries_paused_without_active_experiment",
                active_experiment=experiment_name,
                paper_portfolio_id=str(portfolio.portfolio_id),
            )
        for position in await registry.open_positions():
            feature_engine.pin_mint(position.mint)
            if isinstance(provider, PumpDiscoveryProvider):
                provider.seed_open_position(position.mint)
        if isinstance(provider, PumpPortalDiscoveryProvider):
            budget_day = utc_now().date()
            provider.seed_daily_trade_usage(
                budget_day,
                await registry.provider_event_count_since(
                    provider.descriptor.name,
                    "token.trade",
                    datetime.combine(budget_day, time.min, tzinfo=UTC),
                ),
            )
            for mint, until in (
                await registry.research_watchlist(
                    seconds=settings.research_observation_seconds,
                    sample_percent=settings.research_control_sample_percent,
                )
            ).items():
                market = await registry.paper_market_context(mint, as_of=utc_now())
                if (
                    market is not None
                    and market.normalized_state is not None
                    and research_rejection(
                        market.normalized_state.evidence(),
                        venue=market.venue.value,
                        lifecycle=market.lifecycle.value,
                        mayhem=market.is_mayhem_mode,
                        complete=market.curve_complete,
                    )
                    is None
                ):
                    await provider.observe_research(mint, (until - utc_now()).total_seconds())
            for position in await registry.open_positions():
                provider.seed_open_position(position.mint)
        await risk_coordinator.start()
        if telegram_notifier is not None:
            await telegram_notifier.start()
        pending_sweeper_task = asyncio.create_task(
            sweep_pending_actions(), name="paper-pending-sweeper"
        )
        position_monitor_task = asyncio.create_task(
            monitor_paper_positions(), name="paper-position-monitor"
        )
        wallet_projection_task = asyncio.create_task(
            wallet_projector.run(),
            name="wallet-intelligence-projection",
        )
        seeds = await registry.provider_seeds()
        for seed in seeds["bonding_curves"]:
            provider.seed_bonding_curve(
                seed["mint"],
                seed["bonding_curve"],
                seed["initial_real_reserves"],
                progress_percent=cast(Decimal | None, seed["progress_percent"]),
            )
            feature_engine.seed_lifecycle(
                seed["mint"],
                lifecycle=MarketLifecycle(seed["lifecycle"]),
                validation_state=MarketValidationState(seed["validation_state"]),
                changed_at=seed["changed_at"],
                source_slot=seed["source_slot"],
                bonding_progress_percent=cast(Decimal | None, seed["progress_percent"]),
                market=seed["market"],
            )
        for seed in seeds["pump_swap_pools"]:
            provider.seed_pump_swap_pool(seed["pool"], seed["mint"], seed["quote_mint"])
            feature_engine.seed_lifecycle(
                seed["mint"],
                lifecycle=MarketLifecycle(seed["lifecycle"]),
                validation_state=MarketValidationState(seed["validation_state"]),
                changed_at=seed["changed_at"],
                source_slot=seed["source_slot"],
                bonding_progress_percent=None,
                market=seed["market"],
            )
        capability_report = await provider.probe_capabilities()
        if ollama_policy is not None:
            try:
                logger.info("ollama_model_warming", model=ollama_policy.model)
                await ollama_policy.warmup()
                logger.info("ollama_model_ready", model=ollama_policy.model)
            except Exception as exc:
                logger.warning(
                    "ollama_model_unavailable",
                    model=ollama_policy.model,
                    error_type=type(exc).__name__,
                    detail=str(exc)[:160],
                )
        logger.info(
            "discovery_worker_starting",
            execution_mode=settings.execution_mode,
            confirmed_capabilities=sorted(item.value for item in capability_report.confirmed),
            unknown_capabilities=sorted(item.value for item in capability_report.unknown),
            restored_curves=len(seeds["bonding_curves"]),
            restored_pools=len(seeds["pump_swap_pools"]),
            paper_portfolio_id=str(portfolio.portfolio_id),
            paper_currency=portfolio.currency,
            experiment=(experiment_name if experiment_matches_portfolio else None),
            wallet_backfill="scheduled",
        )
        if on_ready is not None:
            await on_ready()
        if executed_cache is not None:
            executed_cache_task = asyncio.create_task(executed_cache.run(), name="executed-cache")
            executed_watch_task = asyncio.create_task(
                executed_cache.maintain(), name="executed-watch"
            )
            executed_processor_task = asyncio.create_task(
                executed_cache.process(), name="executed-processor"
            )
        if run_seconds is None:
            await provider.run(bus.publish)
        else:
            try:
                async with asyncio.timeout(run_seconds):
                    await provider.run(bus.publish)
            except TimeoutError:
                logger.info("discovery_worker_time_limit_reached", run_seconds=run_seconds)
    finally:
        for task in (
            pending_sweeper_task,
            wallet_backfill_task,
            wallet_projection_task,
            position_monitor_task,
            paper_trade_task,
            executed_cache_task,
            executed_watch_task,
            executed_processor_task,
        ):
            if task is not None:
                task.cancel()
        await asyncio.gather(
            *(
                task
                for task in (
                    pending_sweeper_task,
                    wallet_backfill_task,
                    wallet_projection_task,
                    position_monitor_task,
                    paper_trade_task,
                    executed_cache_task,
                    executed_watch_task,
                    executed_processor_task,
                )
                if task is not None
            ),
            return_exceptions=True,
        )
        if telegram_notifier is not None:
            await telegram_notifier.close()
        await risk_coordinator.close()
        await paper_engine.close()
        await alpha_filter.close()
        if ollama_policy is not None:
            await ollama_policy.close()
        await provider.close()
        await rpc.close()
        await exit_rpc.close()
        await database.dispose()


def _telegram_notifier(
    settings: Settings, registry: TokenRegistry | None = None
) -> TelegramTradeNotifier | None:
    if (
        not (
            settings.telegram_trade_notifications_enabled
            or settings.telegram_tracked_wallet_notifications_enabled
        )
        or settings.telegram_bot_token is None
        or not settings.telegram_allowed_user_ids
    ):
        return None
    return TelegramTradeNotifier(
        settings.telegram_bot_token.get_secret_value(),
        settings.telegram_allowed_user_ids,
        queue_size=settings.telegram_notification_queue_size,
        minimum_interval_seconds=(settings.telegram_notification_minimum_interval_seconds),
        duplicate_cooldown_seconds=(settings.telegram_notification_duplicate_cooldown_seconds),
        event_notifications_enabled=settings.telegram_trade_notifications_enabled,
        token_lookup=registry.token_identity if registry is not None else None,
    )


def _risk_prefilter_passes(settings: Settings, snapshot: object) -> bool:
    """Use free stream-derived features before spending RPC credits on risk."""
    return _risk_prefilter_evaluation(settings, snapshot)[0]


def _risk_prefilter_evaluation(
    settings: Settings, snapshot: object
) -> tuple[bool, tuple[str, ...], RollingWindowMetrics | None]:
    if not isinstance(snapshot, MarketFeatureSnapshotCreated):
        return False, ("feature_snapshot_unavailable",), None
    eligible = [
        window
        for window in snapshot.windows
        if window.window_seconds <= settings.risk_prefilter_window_seconds
    ]
    if not eligible:
        return False, ("prefilter_window_unavailable",), None
    window = max(eligible, key=lambda item: item.window_seconds)
    reasons: list[str] = []
    if window.trade_count < settings.risk_prefilter_min_trades:
        reasons.append("trade_count_below_minimum")
    if window.unique_buyers < settings.risk_prefilter_min_unique_buyers:
        reasons.append("unique_buyers_below_minimum")
    flow_imbalance = window.flow_imbalance if window.flow_imbalance is not None else Decimal(-1)
    if flow_imbalance < settings.risk_prefilter_min_flow_imbalance:
        reasons.append("flow_imbalance_below_minimum")
    return not reasons, tuple(reasons), window
