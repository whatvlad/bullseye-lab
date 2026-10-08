from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.core.sampling import sampled_mint
from memebot.events.models import (
    DomainEvent,
    MarketFeatureSnapshotCreated,
    PaperOrderCompleted,
    ProviderHealthUpdated,
    StrategyDecisionCreated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenRiskAssessed,
    TokenTrade,
)
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.intelligence.risk.models import LocalRiskContext
from memebot.market_price import trade_mark
from memebot.market_state import NormalizedMarketState
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.models.paper import PaperFill, PaperOrderSide, PaperOrderStatus, PositionEffect
from memebot.models.strategy import StrategyConfiguration
from memebot.paper.models import (
    ExecutionMarketSnapshot,
    PortfolioRiskSnapshot,
    PortfolioSnapshot,
    PositionSnapshot,
)
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, WRAPPED_SOL_MINT
from memebot.storage.database.models import (
    DomainEventRecord,
    ExperimentRunRecord,
    MarketFeatureSnapshotRecord,
    MarketRecord,
    PaperOrderRecord,
    PaperPortfolioRecord,
    PaperPositionRecord,
    ProviderHealthRecord,
    StrategyConfigurationRecord,
    StrategyDecisionRecord,
    TokenLifecycleEventRecord,
    TokenRecord,
    TokenRiskAssessmentRecord,
    TokenTradeRecord,
    TradeOutcomeRecord,
    TradingControlRecord,
)

if TYPE_CHECKING:
    from memebot.storage.database.outcomes import OutcomeRecorder


class TokenRegistry:
    """Idempotently projects immutable domain events into queryable token state."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        max_mark_age_seconds: int = 5,
        outcome_recorder: OutcomeRecorder | None = None,
    ) -> None:
        self._sessions = sessions
        self._max_mark_age_seconds = max_mark_age_seconds
        self._outcome_recorder = outcome_recorder

    async def provider_event_count_since(
        self, provider: str, event_type: str, since: datetime
    ) -> int:
        """Count persisted provider events for restart-safe usage budgets."""
        async with self._sessions() as session:
            count = await session.scalar(
                select(func.count(DomainEventRecord.event_id)).where(
                    DomainEventRecord.provider == provider,
                    DomainEventRecord.event_type == event_type,
                    DomainEventRecord.source_event_at >= since,
                )
            )
        return int(count or 0)

    async def handle(self, event: DomainEvent) -> bool:
        async with self._sessions() as session:
            try:
                async with session.begin():
                    if await session.get(DomainEventRecord, event.event_id) is not None:
                        return False
                    session.add(
                        DomainEventRecord(
                            event_id=event.event_id,
                            event_type=event.event_type.value,
                            schema_version=event.schema_version,
                            provider=event.provider,
                            source_event_at=event.source_event_at,
                            provider_received_at=event.provider_received_at,
                            ingested_at=event.ingested_at,
                            correlation_id=event.correlation_id,
                            source_sequence=event.source_sequence,
                            source_signature=event.source_signature,
                            source_slot=event.source_slot,
                            payload=event.model_dump(mode="json"),
                        )
                    )
                    if isinstance(event, TokenDiscovered):
                        await self._apply_discovery(session, event)
                    elif isinstance(event, TokenLifecycleChanged):
                        await self._apply_lifecycle(session, event)
                    elif isinstance(event, TokenTrade):
                        await self._apply_trade(session, event)
                    elif isinstance(event, MarketFeatureSnapshotCreated):
                        await self._apply_feature_snapshot(session, event)
                    elif isinstance(event, TokenRiskAssessed):
                        await self._apply_risk_assessment(session, event)
                    elif isinstance(event, StrategyDecisionCreated):
                        await self._apply_strategy_decision(session, event)
                    elif isinstance(event, PaperOrderCompleted):
                        await self._apply_paper_order(session, event)
                    elif isinstance(event, ProviderHealthUpdated):
                        await self._apply_provider_health(session, event)
                    if self._outcome_recorder is not None:
                        await self._outcome_recorder.handle_in_session(session, event)
            except IntegrityError:
                # Another worker may have committed this deterministic event first.
                async with self._sessions() as verification_session:
                    duplicate = await verification_session.get(DomainEventRecord, event.event_id)
                if duplicate is not None:
                    return False
                raise
        return True

    async def _apply_discovery(
        self,
        session: AsyncSession,
        event: TokenDiscovered,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        if event.name:
            token.name = event.name
        if event.symbol:
            token.symbol = event.symbol
        if event.creator:
            token.creator = event.creator
        if event.launch_venue != LaunchVenue.UNKNOWN:
            token.launch_venue = event.launch_venue.value
        token.source_created_at = token.source_created_at or event.source_event_at
        self._update_observation_position(token, event)
        metadata = dict(token.metadata_json or {})
        for key, value in {
            "bonding_curve": event.bonding_curve,
            "quote_mint": event.quote_mint,
            "metadata_uri": event.metadata_uri,
            "initial_real_token_reserves": event.initial_real_token_reserves,
            "token_total_supply": event.token_total_supply,
            "is_mayhem_mode": event.is_mayhem_mode,
            "entry_rejection_reason": event.entry_rejection_reason,
        }.items():
            if value is not None:
                metadata[key] = value
        token.metadata_json = metadata or None

    async def _apply_lifecycle(
        self,
        session: AsyncSession,
        event: TokenLifecycleChanged,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        is_current = (
            event.source_slot is None
            or token.last_source_slot is None
            or event.source_slot >= token.last_source_slot
        )
        if is_current:
            token.current_lifecycle = event.lifecycle.value
            token.validation_state = event.validation_state.value
            if event.market:
                token.current_market = event.market
        self._update_observation_position(token, event)
        if event.market:
            await self._upsert_market(session, token, event)
        if event.lifecycle in {
            MarketLifecycle.GRADUATION,
            MarketLifecycle.POST_GRADUATION,
        }:
            token.graduated_at = token.graduated_at or event.source_event_at
        session.add(
            TokenLifecycleEventRecord(
                event_id=event.event_id,
                token_id=token.id,
                lifecycle=event.lifecycle.value,
                validation_state=event.validation_state.value,
                market_address=event.market,
                quote_mint=event.quote_mint,
                bonding_progress_percent=event.bonding_progress_percent,
                real_token_reserves=event.real_token_reserves,
                real_quote_reserves=event.real_quote_reserves,
                reason=event.reason,
                source_signature=event.source_signature,
                source_slot=event.source_slot,
                source_event_at=event.source_event_at,
            )
        )

    async def _apply_trade(self, session: AsyncSession, event: TokenTrade) -> None:
        token = await self._get_or_create_token(session, event.mint)
        self._update_observation_position(token, event)
        session.add(
            TokenTradeRecord(
                event_id=event.event_id,
                token_id=token.id,
                signature=event.signature,
                side=event.side.value,
                token_amount_raw=event.token_amount,
                quote_amount_raw=event.quote_amount,
                price_raw=trade_mark(event),
                quote_asset=event.quote_asset,
                quote_mint=event.quote_mint,
                wallet=event.wallet,
                market_address=event.market,
                real_token_reserves=event.real_token_reserves,
                real_quote_reserves=event.real_quote_reserves,
                virtual_token_reserves=(
                    Decimal(event.virtual_token_reserves)
                    if event.virtual_token_reserves is not None
                    else None
                ),
                virtual_quote_reserves=(
                    Decimal(event.virtual_quote_reserves)
                    if event.virtual_quote_reserves is not None
                    else None
                ),
                source_slot=event.source_slot,
                source_event_at=event.source_event_at,
            )
        )
        # Stream excursions are projected separately by the outcomes repository.
        # Only quantity-specific execution marks may update open-position exits.

    async def _apply_feature_snapshot(
        self,
        session: AsyncSession,
        event: MarketFeatureSnapshotCreated,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        session.add(
            MarketFeatureSnapshotRecord(
                event_id=event.event_id,
                token_id=token.id,
                trigger_event_id=event.trigger_event_id,
                observed_at=event.source_event_at,
                lifecycle=event.lifecycle.value,
                validation_state=event.validation_state.value,
                lifecycle_age_seconds=event.lifecycle_age_seconds,
                bonding_progress_percent=event.bonding_progress_percent,
                market_address=event.market,
                latest_price_raw=event.latest_price_raw,
                windows_json=[window.model_dump(mode="json") for window in event.windows],
                source_slot=event.source_slot,
            )
        )

    async def _apply_risk_assessment(
        self,
        session: AsyncSession,
        event: TokenRiskAssessed,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        result = event.result
        session.add(
            TokenRiskAssessmentRecord(
                event_id=event.event_id,
                token_id=token.id,
                trigger_event_id=event.trigger_event_id,
                assessed_at=event.source_event_at,
                allowed=result.allowed,
                risk_score=result.risk_score,
                data_completeness_percent=result.data_completeness_percent,
                hard_reject_reasons=list(result.hard_reject_reasons),
                warnings=list(result.warnings),
                critical_unknowns=list(result.critical_unknowns),
                evidence_json=[item.model_dump(mode="json") for item in result.evidence],
                market_address=event.market,
                source_slot=event.source_slot,
            )
        )
        current_assessed_at = token.risk_assessed_at
        if current_assessed_at is not None and current_assessed_at.tzinfo is None:
            current_assessed_at = current_assessed_at.replace(tzinfo=UTC)
        if current_assessed_at is None or event.source_event_at >= current_assessed_at:
            token.risk_allowed = result.allowed
            token.risk_score = result.risk_score
            token.risk_assessed_at = event.source_event_at
            token.risk_assessment_event_id = event.event_id

    async def _apply_strategy_decision(
        self,
        session: AsyncSession,
        event: StrategyDecisionCreated,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        session.add(
            StrategyDecisionRecord(
                event_id=event.event_id,
                token_id=token.id,
                strategy_version_id=event.strategy_version_id,
                strategy_key=event.strategy_key,
                active_strategy=event.active_strategy,
                action=event.action.value,
                regime=event.regime.value,
                risk_event_id=event.risk_event_id,
                feature_event_id=event.feature_event_id,
                decided_at=event.source_event_at,
                final_score=event.score.final_score,
                component_completeness_percent=(event.score.component_completeness_percent),
                score_components_json=[
                    item.model_dump(mode="json") for item in event.score.components
                ],
                reasons=list(event.reasons),
                source_slot=event.source_slot,
            )
        )

    async def _apply_paper_order(
        self,
        session: AsyncSession,
        event: PaperOrderCompleted,
    ) -> None:
        token = await self._get_or_create_token(session, event.mint)
        result = event.result
        fill = result.fill
        session.add(
            PaperOrderRecord(
                event_id=event.event_id,
                portfolio_id=event.portfolio_id,
                token_id=token.id,
                mint=event.mint,
                trigger_event_id=event.trigger_event_id,
                decision_event_id=event.decision_event_id,
                strategy_key=event.strategy_key,
                side=result.side.value,
                status=result.status.value,
                position_effect=result.position_effect.value,
                rejection_reason=result.rejection_reason,
                exit_reason=result.exit_reason,
                market_address=event.market,
                venue=event.venue.value,
                lifecycle=event.lifecycle.value,
                requested_portfolio_amount=result.requested_portfolio_amount,
                signal_at=fill.signal_at if fill is not None else event.source_event_at,
                decision_at=fill.decision_at if fill is not None else event.source_event_at,
                submitted_at=fill.submitted_at if fill is not None else None,
                filled_at=fill.filled_at if fill is not None else None,
                fill_json=fill.model_dump(mode="json") if fill is not None else None,
                created_at=event.ingested_at,
            )
        )
        if result.status != PaperOrderStatus.FILLED or fill is None:
            return
        if event.market is None:
            raise ValueError("filled paper order requires market")
        portfolio = await session.get(
            PaperPortfolioRecord, event.portfolio_id, with_for_update=True
        )
        if portfolio is None:
            raise ValueError("paper portfolio not found")
        network_fee = (
            fill.network_fee_quote_raw
            / Decimal(1_000_000_000)
            * fill.quote_price_in_portfolio_currency
        )
        execution_provider_fee = (
            fill.execution_provider_fee_quote_raw
            / Decimal(1_000_000_000)
            * fill.quote_price_in_portfolio_currency
        )
        if result.side == PaperOrderSide.BUY:
            total_cost = fill.gross_portfolio_amount + network_fee + execution_provider_fee
            if portfolio.cash_balance < total_cost:
                raise ValueError("paper portfolio cash changed before fill projection")
            existing = await session.scalar(
                select(PaperPositionRecord).where(
                    PaperPositionRecord.portfolio_id == portfolio.id,
                    PaperPositionRecord.mint == event.mint,
                    PaperPositionRecord.status == "open",
                )
            )
            if existing is not None:
                raise ValueError("paper position already open")
            portfolio.cash_balance -= total_cost
            session.add(
                PaperPositionRecord(
                    portfolio_id=portfolio.id,
                    token_id=token.id,
                    mint=event.mint,
                    strategy_key=event.strategy_key,
                    market_address=event.market,
                    venue=event.venue.value,
                    lifecycle=event.lifecycle.value,
                    status="open",
                    token_quantity_raw=fill.token_amount_raw,
                    remaining_cost_basis=total_cost,
                    realized_pnl=Decimal(0),
                    entry_price_raw=fill.actual_fill_price_raw,
                    peak_price_raw=fill.actual_fill_price_raw,
                    last_price_raw=fill.actual_fill_price_raw,
                    opened_at=fill.filled_at,
                    mark_observed_at=fill.filled_at,
                    partial_take_profit_taken=False,
                )
            )
            return
        position = await session.scalar(
            select(PaperPositionRecord).where(
                PaperPositionRecord.portfolio_id == portfolio.id,
                PaperPositionRecord.mint == event.mint,
                PaperPositionRecord.status == "open",
            )
        )
        if position is None or position.token_quantity_raw < fill.token_amount_raw:
            raise ValueError("paper position unavailable for sell fill")
        if (
            result.position_effect == PositionEffect.CLOSE
            and fill.token_amount_raw != position.token_quantity_raw
        ):
            raise ValueError("full close must sell the entire remaining quantity")
        if result.position_effect not in {PositionEffect.CLOSE, PositionEffect.PARTIAL_CLOSE}:
            raise ValueError("sell fill requires a close position effect")
        fraction = fill.token_amount_raw / position.token_quantity_raw
        allocated_cost = position.remaining_cost_basis * fraction
        proceeds = fill.gross_portfolio_amount - fill.total_fee_portfolio
        realized = proceeds - allocated_cost
        portfolio.cash_balance += proceeds
        portfolio.realized_pnl += realized
        position.token_quantity_raw -= fill.token_amount_raw
        position.remaining_cost_basis -= allocated_cost
        position.realized_pnl += realized
        position.last_price_raw = fill.actual_fill_price_raw
        if result.position_effect == PositionEffect.PARTIAL_CLOSE:
            position.partial_take_profit_taken = True
        else:
            position.status = "closed"
            position.closed_at = fill.filled_at
            position.token_quantity_raw = Decimal(0)
            position.remaining_cost_basis = Decimal(0)

    async def ensure_default_paper_portfolio(
        self, *, initial_cash: Decimal, currency: str
    ) -> PortfolioSnapshot:
        async with self._sessions() as session, session.begin():
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                portfolio = PaperPortfolioRecord(
                    name="Default paper portfolio",
                    currency=currency,
                    initial_cash=initial_cash,
                    cash_balance=initial_cash,
                    realized_pnl=Decimal(0),
                    active=True,
                )
                session.add(portfolio)
                await session.flush()
            return await _portfolio_snapshot(session, portfolio)

    async def create_paper_portfolio(
        self,
        *,
        name: str,
        initial_cash: Decimal,
        currency: str,
        settings_snapshot: dict[str, object] | None = None,
    ) -> PortfolioSnapshot:
        async with self._sessions() as session, session.begin():
            active = (
                await session.scalars(
                    select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
                )
            ).all()
            exposure = await session.scalar(
                select(func.count())
                .select_from(PaperPositionRecord)
                .where(PaperPositionRecord.status == "open")
            )
            if exposure:
                raise ValueError("close all open paper positions before resetting the portfolio")
            control = await session.get(TradingControlRecord, 1)
            if control is not None:
                control.entries_paused = True
                control.updated_by_telegram_user_id = 0
            for item in active:
                item.active = False
            portfolio = PaperPortfolioRecord(
                name=name,
                currency=currency,
                initial_cash=initial_cash,
                cash_balance=initial_cash,
                realized_pnl=Decimal(0),
                active=True,
            )
            session.add(portfolio)
            await session.flush()
            experiment = await session.scalar(
                select(ExperimentRunRecord).where(ExperimentRunRecord.status == "active")
            )
            strategy = (
                await session.scalar(
                    select(StrategyConfigurationRecord)
                    .where(StrategyConfigurationRecord.strategy_key == control.active_strategy_key)
                    .order_by(StrategyConfigurationRecord.version.desc())
                    .limit(1)
                )
                if control is not None
                else None
            )
            if experiment is not None or strategy is not None:
                now = datetime.now(UTC)
                if experiment is not None:
                    experiment.status, experiment.stopped_at = "stopped", now
                snapshot = dict(experiment.configuration_snapshot_json) if experiment else {}
                snapshot["portfolio_reset"] = {
                    "parent_experiment_id": str(experiment.id) if experiment else None,
                    "previous_portfolio_id": str(active[0].id) if active else None,
                    "reset_at": now.isoformat(),
                }
                snapshot["captured_at"] = now.isoformat()
                if settings_snapshot is not None:
                    snapshot["settings"] = {
                        key: value
                        for key, value in settings_snapshot.items()
                        if key != "database_url"
                    }
                if control is not None:
                    snapshot["trading_control"] = {
                        key: str(getattr(control, key))
                        if key.endswith("percent")
                        else getattr(control, key)
                        for key in (
                            "active_strategy_key",
                            "base_position_percent",
                            "max_position_percent",
                            "max_open_positions",
                            "stop_loss_percent",
                            "take_profit_percent",
                            "trailing_stop_percent",
                            "max_holding_seconds",
                        )
                    }
                if strategy is not None:
                    snapshot["strategy"] = {
                        **strategy.configuration_json,
                        "active_for_execution": True,
                        "activation_source": "trading_control",
                    }
                from memebot import __version__

                if strategy is not None:
                    strategy_key, strategy_id = strategy.strategy_key, strategy.version_id
                else:
                    assert experiment is not None
                    strategy_key, strategy_id = (
                        experiment.strategy_key,
                        experiment.strategy_version_id,
                    )
                session.add(
                    ExperimentRunRecord(
                        name=f"{experiment.name[:75] if experiment else 'paper'}"
                        f"-reset-{portfolio.id.hex[:8]}",
                        status="active",
                        portfolio_id=portfolio.id,
                        strategy_key=strategy_key,
                        strategy_version_id=strategy_id,
                        application_version=__version__,
                        configuration_snapshot_json=snapshot,
                        started_at=now,
                        notes=(
                            "Explicit Telegram portfolio reset; linked child cohort, "
                            "entries paused; prior results retained."
                        ),
                    )
                )
            return await _portfolio_snapshot(session, portfolio)

    async def active_paper_portfolio(self) -> PortfolioSnapshot | None:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            return await _portfolio_snapshot(session, portfolio) if portfolio is not None else None

    async def paper_risk_snapshot(
        self, mint: str, *, as_of: datetime
    ) -> PortfolioRiskSnapshot | None:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                return None
            positions = (
                await session.scalars(
                    select(PaperPositionRecord)
                    .where(PaperPositionRecord.portfolio_id == portfolio.id)
                    .order_by(PaperPositionRecord.closed_at.desc())
                )
            ).all()
            opened = [item for item in positions if item.status == "open"]
            closed = [item for item in positions if item.status == "closed"]
            open_cost = sum((item.remaining_cost_basis for item in opened), start=Decimal(0))
            unrealized = sum(
                (
                    Decimal(str(item.execution_mark_json["net_portfolio_value"]))
                    - item.remaining_cost_basis
                    for item in opened
                    if item.execution_mark_json is not None
                ),
                start=Decimal(0),
            )
            day_start = as_of.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            daily_realized = sum(
                (
                    item.realized_pnl
                    for item in positions
                    if item.realized_pnl != 0
                    and (
                        (item.closed_at is not None and _as_utc(item.closed_at) >= day_start)
                        or (item.status == "open" and _as_utc(item.updated_at) >= day_start)
                    )
                ),
                start=Decimal(0),
            )
            consecutive_losses = 0
            for item in closed:
                if item.realized_pnl < 0:
                    consecutive_losses += 1
                else:
                    break
            return PortfolioRiskSnapshot(
                portfolio_id=portfolio.id,
                initial_cash=portfolio.initial_cash,
                open_cost_basis=open_cost,
                unrealized_pnl=unrealized,
                execution_marks_valid=all(
                    item.execution_mark_json is not None
                    and item.mark_observed_at is not None
                    and 0
                    <= (as_of - _as_utc(item.mark_observed_at)).total_seconds()
                    <= self._max_mark_age_seconds
                    and Decimal(str(item.execution_mark_json["token_amount_raw"]))
                    == item.token_quantity_raw
                    for item in opened
                ),
                daily_realized_pnl=daily_realized,
                consecutive_losses=consecutive_losses,
                last_closed_at=closed[0].closed_at if closed else None,
                mint_last_closed_at=next(
                    (item.closed_at for item in closed if item.mint == mint), None
                ),
            )

    async def paper_market_context(
        self, mint: str, *, as_of: datetime
    ) -> ExecutionMarketSnapshot | None:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
            )
            if token is None:
                return None
            trade = await session.scalar(
                select(TokenTradeRecord)
                .where(
                    TokenTradeRecord.token_id == token.id,
                    TokenTradeRecord.source_event_at <= as_of,
                )
                .order_by(TokenTradeRecord.source_event_at.desc())
                .limit(1)
            )
            if trade is None or (token.current_market or trade.market_address) is None:
                return None
            address = token.current_market or trade.market_address
            assert address is not None
            migrated = address != trade.market_address
            market = await session.scalar(
                select(MarketRecord).where(
                    MarketRecord.network == "solana",
                    MarketRecord.address == address,
                )
            )
            venue = LaunchVenue(market.venue) if market is not None else LaunchVenue.UNKNOWN
            domain = await session.get(DomainEventRecord, trade.event_id)
            normalized = NormalizedMarketState.model_validate(
                domain.payload.get("normalized_state", {}) if domain and not migrated else {}
            )
            received = (domain.provider_received_at or domain.ingested_at) if domain else None
            reserve_mark = (
                bool(
                    (trade.virtual_token_reserves and trade.virtual_quote_reserves)
                    or (trade.real_token_reserves and trade.real_quote_reserves)
                )
                and not migrated
                and normalized.observational_price is not None
            )
            return ExecutionMarketSnapshot(
                normalized_state=normalized,
                is_mayhem_mode=normalized.is_mayhem_mode
                if normalized.is_mayhem_mode is not None
                else (token.metadata_json or {}).get("is_mayhem_mode"),
                mint=mint,
                market=address,
                venue=venue,
                lifecycle=MarketLifecycle(token.current_lifecycle),
                observed_at=_as_utc(trade.source_event_at),
                source_slot=trade.source_slot,
                observed_price_raw=trade.price_raw,
                quote_asset=(
                    WRAPPED_SOL_MINT
                    if (trade.quote_mint or trade.quote_asset) == NATIVE_SOL_MINT
                    else trade.quote_mint or trade.quote_asset
                ),
                real_token_reserves_raw=None if migrated else trade.real_token_reserves,
                real_quote_reserves_raw=None if migrated else trade.real_quote_reserves,
                virtual_token_reserves_raw=(
                    int(trade.virtual_token_reserves)
                    if trade.virtual_token_reserves is not None and not migrated
                    else None
                ),
                virtual_quote_reserves_raw=(
                    int(trade.virtual_quote_reserves)
                    if trade.virtual_quote_reserves is not None and not migrated
                    else None
                ),
                price_source="stream_reserves" if reserve_mark else "stream_average_trade",
                source_timestamp=_as_utc(trade.source_event_at),
                received_timestamp=_as_utc(received) if received else None,
                feed_timestamp=_as_utc(trade.source_event_at),
                feed_timestamp_estimated=bool(
                    domain is None
                    or "pumpportal" in domain.provider
                    or domain.payload.get("source_timestamp_estimated", False)
                ),
                feed_reference_price=trade.price_raw if reserve_mark else None,
                data_quality=(
                    "source_time_estimated"
                    if domain and domain.payload.get("source_timestamp_estimated", False)
                    else "stream_slot_known"
                    if reserve_mark
                    else "average_trade_only"
                ),
            )

    async def feature_observed_at(self, event_id: UUID) -> datetime | None:
        async with self._sessions() as session:
            record = await session.get(MarketFeatureSnapshotRecord, event_id)
            return record.observed_at if record is not None else None

    async def open_position(self, mint: str) -> PositionSnapshot | None:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                return None
            position = await session.scalar(
                select(PaperPositionRecord).where(
                    PaperPositionRecord.portfolio_id == portfolio.id,
                    PaperPositionRecord.mint == mint,
                    PaperPositionRecord.status == "open",
                )
            )
            return _position_snapshot(position) if position is not None else None

    async def open_positions(self) -> list[PositionSnapshot]:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                return []
            positions = (
                await session.scalars(
                    select(PaperPositionRecord).where(
                        PaperPositionRecord.portfolio_id == portfolio.id,
                        PaperPositionRecord.status == "open",
                    )
                )
            ).all()
            return [_position_snapshot(item) for item in positions]

    async def reconcile_zero_quantity_positions(self, *, closed_at: datetime | None = None) -> int:
        """Close legacy dust rows left open by a concurrent partial-exit race."""
        repaired = 0
        timestamp = closed_at or datetime.now(UTC)
        async with self._sessions() as session, session.begin():
            positions = (
                await session.scalars(
                    select(PaperPositionRecord).where(
                        PaperPositionRecord.status == "open",
                        PaperPositionRecord.token_quantity_raw <= 0,
                        PaperPositionRecord.remaining_cost_basis <= 0,
                    )
                )
            ).all()
            for position in positions:
                position.status = "closed"
                position.closed_at = timestamp
                position.token_quantity_raw = Decimal(0)
                position.remaining_cost_basis = Decimal(0)
                repaired += 1
        return repaired

    async def observe_open_position_price(
        self,
        position_id: UUID,
        price: Decimal,
        *,
        observed_at: datetime | None = None,
        execution_fill: PaperFill | None = None,
    ) -> None:
        if price <= 0:
            return
        async with self._sessions() as session, session.begin():
            position = await session.get(PaperPositionRecord, position_id)
            if position is None or position.status != "open":
                return
            timestamp = observed_at or datetime.now(UTC)
            if timestamp < _as_utc(position.opened_at) or (
                position.mark_observed_at and timestamp < _as_utc(position.mark_observed_at)
            ):
                return
            position.last_price_raw = price
            position.peak_price_raw = max(position.peak_price_raw, price)
            position.mark_observed_at = timestamp
            prior_mark = position.execution_mark_json or {}
            exit_evidence = prior_mark.get("exit_evidence", {})
            statistics = dict(prior_mark.get("executable_statistics", {}))
            if execution_fill is not None and position.remaining_cost_basis > 0:
                from memebot.paper.exit_evidence import retain_exit_evidence

                exit_evidence = retain_exit_evidence(
                    prior_mark,
                    execution_fill,
                    quantity=position.token_quantity_raw,
                    cost_basis=position.remaining_cost_basis,
                    entry_price=position.entry_price_raw,
                    opened_at=_as_utc(position.opened_at),
                )
                net_value = (
                    execution_fill.gross_portfolio_amount - execution_fill.total_fee_portfolio
                )
                current_return = (net_value / position.remaining_cost_basis - 1) * 100
                peak = Decimal(str(statistics.get("mfe_percent", current_return)))
                trough = Decimal(str(statistics.get("mae_percent", current_return)))
                if not statistics or current_return > peak:
                    statistics["peak_at"] = timestamp.isoformat()
                statistics.update(
                    mfe_percent=str(max(peak, current_return)),
                    mae_percent=str(min(trough, current_return)),
                    latest_return_percent=str(current_return),
                    basis="net executable remaining-position liquidation / remaining cost basis",
                )
            position.execution_mark_json = (
                {
                    **execution_fill.model_dump(mode="json"),
                    "net_portfolio_value": str(
                        execution_fill.gross_portfolio_amount - execution_fill.total_fee_portfolio
                    ),
                    "executable_statistics": statistics,
                    "exit_evidence": exit_evidence,
                }
                if execution_fill is not None
                else None
            )

    async def research_watchlist(self, *, seconds: int, sample_percent: int) -> dict[str, datetime]:
        """Restore observation leases from durable closes and sampled rejected decisions."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=seconds)
        result: dict[str, datetime] = {}
        async with self._sessions() as session:
            for trade in (
                await session.scalars(
                    select(TradeOutcomeRecord).where(TradeOutcomeRecord.exit_at >= cutoff)
                )
            ).all():
                if trade.exit_at is not None:
                    result[trade.mint] = _as_utc(trade.exit_at) + timedelta(seconds=seconds)
            decisions = (
                await session.execute(
                    select(StrategyDecisionRecord, TokenRecord.mint)
                    .join(TokenRecord, TokenRecord.id == StrategyDecisionRecord.token_id)
                    .where(
                        StrategyDecisionRecord.decided_at >= cutoff,
                        StrategyDecisionRecord.active_strategy.is_(True),
                        StrategyDecisionRecord.action != "enter_candidate",
                    )
                )
            ).all()
            for decision, mint in decisions:
                if sampled_mint(mint, sample_percent):
                    until = _as_utc(decision.decided_at) + timedelta(seconds=seconds)
                    result[mint] = max(result.get(mint, until), until)
        return result

    async def paper_portfolio_report(self) -> dict[str, Any] | None:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                return None
            position_rows = (
                await session.execute(
                    select(PaperPositionRecord, TokenRecord)
                    .join(TokenRecord, TokenRecord.id == PaperPositionRecord.token_id)
                    .where(
                        PaperPositionRecord.portfolio_id == portfolio.id,
                        PaperPositionRecord.status == "open",
                    )
                    .order_by(PaperPositionRecord.opened_at.desc())
                )
            ).all()
            positions = [row[0] for row in position_rows]
            open_cost = sum(
                (item.remaining_cost_basis for item in positions if item.status == "open"),
                start=Decimal(0),
            )
            reconciled = portfolio.cash_balance + open_cost
            expected = portfolio.initial_cash + portfolio.realized_pnl
            accounting_difference = reconciled - expected
            return {
                "portfolio_id": str(portfolio.id),
                "name": portfolio.name,
                "currency": portfolio.currency,
                "initial_cash": str(portfolio.initial_cash),
                "cash_balance": str(portfolio.cash_balance),
                "realized_pnl": str(portfolio.realized_pnl),
                "open_cost_basis": str(open_cost),
                "accounting_reconciled": abs(accounting_difference) <= Decimal("0.000001"),
                "accounting_difference": str(accounting_difference),
                "positions": [
                    _position_record_payload(
                        position, token, max_mark_age_seconds=self._max_mark_age_seconds
                    )
                    for position, token in position_rows
                ],
            }

    async def latest_paper_orders(self, *, limit: int = 20) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if portfolio is None:
                return []
            records = (
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(PaperOrderRecord.portfolio_id == portfolio.id)
                    .order_by(PaperOrderRecord.created_at.desc())
                    .limit(limit)
                )
            ).all()
        return [_paper_order_record_payload(item) for item in records]

    async def token_identity(self, mint: str) -> dict[str, Any] | None:
        async with self._sessions() as session:
            token = await session.scalar(select(TokenRecord).where(TokenRecord.mint == mint))
            return (
                {"name": token.name, "symbol": token.symbol, "mint": token.mint} if token else None
            )

    async def paper_history(self, page: int = 0) -> dict[str, Any]:
        from .paper_history import PaperHistoryRepository

        return await PaperHistoryRepository(self._sessions).page(page)

    async def paper_position_history(
        self, position_id: str, page: int = 0
    ) -> dict[str, Any] | None:
        from .paper_history import PaperHistoryRepository

        return await PaperHistoryRepository(self._sessions).detail(position_id, page)

    async def paper_history_csv(self) -> bytes:
        from .paper_history import PaperHistoryRepository

        return await PaperHistoryRepository(self._sessions).csv()

    async def paper_history_archive(self) -> bytes:
        from .paper_history import PaperHistoryRepository

        return await PaperHistoryRepository(self._sessions).archive()

    async def ensure_strategy_configurations(
        self, configurations: tuple[StrategyConfiguration, ...]
    ) -> None:
        async with self._sessions() as session, session.begin():
            for configuration in configurations:
                record = await session.get(StrategyConfigurationRecord, configuration.version_id)
                if record is None:
                    session.add(
                        StrategyConfigurationRecord(
                            version_id=configuration.version_id,
                            strategy_key=configuration.key,
                            display_name=configuration.display_name,
                            version=configuration.version,
                            enabled=configuration.enabled,
                            active_for_execution=configuration.active_for_execution,
                            configuration_json=configuration.model_dump(mode="json"),
                        )
                    )

    async def strategy_configurations(self) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(StrategyConfigurationRecord)
                    .where(StrategyConfigurationRecord.enabled.is_(True))
                    .order_by(
                        StrategyConfigurationRecord.strategy_key,
                        StrategyConfigurationRecord.version,
                    )
                )
            ).all()
            return [
                {
                    "version_id": str(item.version_id),
                    "strategy_key": item.strategy_key,
                    "display_name": item.display_name,
                    "version": item.version,
                    "enabled": item.enabled,
                    "active_for_execution": item.active_for_execution,
                    "configuration": item.configuration_json,
                }
                for item in records
            ]

    async def strategy_context(
        self, mint: str, *, as_of: datetime
    ) -> tuple[MarketFeatureSnapshotCreated | None, datetime | None]:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
            )
            if token is None:
                return None, None
            record = await session.scalar(
                select(MarketFeatureSnapshotRecord)
                .where(
                    MarketFeatureSnapshotRecord.token_id == token.id,
                    MarketFeatureSnapshotRecord.observed_at <= as_of,
                )
                .order_by(MarketFeatureSnapshotRecord.observed_at.desc())
                .limit(1)
            )
            if record is None:
                return None, token.source_created_at
            original = await session.get(DomainEventRecord, record.event_id)
            feature = MarketFeatureSnapshotCreated(
                price_evidence=(original.payload.get("price_evidence", {}) if original else {}),
                event_id=record.event_id,
                provider="rolling_feature_engine",
                source_event_at=_as_utc(record.observed_at),
                source_slot=record.source_slot,
                mint=token.mint,
                trigger_event_id=record.trigger_event_id,
                lifecycle=MarketLifecycle(record.lifecycle),
                validation_state=MarketValidationState(record.validation_state),
                lifecycle_age_seconds=record.lifecycle_age_seconds,
                bonding_progress_percent=record.bonding_progress_percent,
                market=record.market_address,
                latest_price_raw=record.latest_price_raw,
                windows=tuple(
                    RollingWindowMetrics.model_validate(item) for item in record.windows_json
                ),
            )
            return feature, token.source_created_at

    @staticmethod
    async def _upsert_market(
        session: AsyncSession,
        token: TokenRecord,
        event: TokenLifecycleChanged,
    ) -> None:
        assert event.market is not None
        market = await session.scalar(
            select(MarketRecord).where(
                MarketRecord.network == "solana",
                MarketRecord.address == event.market,
            )
        )
        venue = (
            LaunchVenue.PUMP_SWAP
            if event.lifecycle == MarketLifecycle.POST_GRADUATION
            else LaunchVenue.PUMP_FUN
        )
        if market is None:
            session.add(
                MarketRecord(
                    token_id=token.id,
                    address=event.market,
                    venue=venue.value,
                    quote_mint=event.quote_mint,
                    status=event.lifecycle.value,
                    source_created_at=event.source_event_at,
                )
            )
            return
        market.token_id = token.id
        market.quote_mint = event.quote_mint or market.quote_mint
        lifecycle_order = {
            MarketLifecycle.UNKNOWN.value: 0,
            MarketLifecycle.NEW_LAUNCH.value: 1,
            MarketLifecycle.BONDING_CURVE.value: 2,
            MarketLifecycle.FINAL_STRETCH.value: 3,
            MarketLifecycle.GRADUATION.value: 4,
            MarketLifecycle.POST_GRADUATION.value: 5,
            MarketLifecycle.MATURE.value: 6,
            MarketLifecycle.DEAD_OR_ILLIQUID.value: 7,
        }
        if lifecycle_order.get(event.lifecycle.value, 0) >= lifecycle_order.get(market.status, 0):
            market.venue = venue.value
            market.status = event.lifecycle.value

    @staticmethod
    async def _apply_provider_health(
        session: AsyncSession,
        event: ProviderHealthUpdated,
    ) -> None:
        record = await session.scalar(
            select(ProviderHealthRecord).where(ProviderHealthRecord.provider == event.provider)
        )
        if record is None:
            record = ProviderHealthRecord(
                provider=event.provider,
                state=event.state.value,
                confirmed_capabilities=sorted(event.confirmed_capabilities),
                unavailable_capabilities=sorted(event.unavailable_capabilities),
                last_checked_at=event.source_event_at,
            )
            session.add(record)
        record.state = event.state.value
        record.confirmed_capabilities = sorted(event.confirmed_capabilities)
        record.unavailable_capabilities = sorted(event.unavailable_capabilities)
        record.last_checked_at = event.source_event_at
        record.last_event_at = event.source_event_at
        record.reconnect_count = event.reconnect_count
        record.average_message_latency_ms = (
            float(event.average_message_latency_ms)
            if event.average_message_latency_ms is not None
            else None
        )
        record.rate_limited = event.rate_limited
        record.error_code = event.error_code
        record.error_message = event.error_message

    @staticmethod
    async def _get_or_create_token(session: AsyncSession, mint: str) -> TokenRecord:
        token = await session.scalar(
            select(TokenRecord).where(
                TokenRecord.network == "solana",
                TokenRecord.mint == mint,
            )
        )
        if token is None:
            token = TokenRecord(mint=mint)
            session.add(token)
            await session.flush()
        return token

    @staticmethod
    def _update_observation_position(token: TokenRecord, event: DomainEvent) -> None:
        last_seen = token.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        token.last_seen_at = max(last_seen, event.source_event_at)
        if event.source_slot is not None:
            token.last_source_slot = max(token.last_source_slot or 0, event.source_slot)

    async def inspect_token(self, mint: str) -> dict[str, Any] | None:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(
                    TokenRecord.network == "solana",
                    TokenRecord.mint == mint,
                )
            )
            if token is None:
                return None
            markets = (
                await session.scalars(
                    select(MarketRecord)
                    .where(MarketRecord.token_id == token.id)
                    .order_by(MarketRecord.source_created_at)
                )
            ).all()
            lifecycle = (
                await session.scalars(
                    select(TokenLifecycleEventRecord)
                    .where(TokenLifecycleEventRecord.token_id == token.id)
                    .order_by(TokenLifecycleEventRecord.source_event_at.desc())
                    .limit(20)
                )
            ).all()
            latest_feature = await session.scalar(
                select(MarketFeatureSnapshotRecord)
                .where(MarketFeatureSnapshotRecord.token_id == token.id)
                .order_by(MarketFeatureSnapshotRecord.observed_at.desc())
                .limit(1)
            )
            latest_risk = await session.scalar(
                select(TokenRiskAssessmentRecord)
                .where(TokenRiskAssessmentRecord.token_id == token.id)
                .order_by(TokenRiskAssessmentRecord.assessed_at.desc())
                .limit(1)
            )
            return {
                "network": token.network,
                "mint": token.mint,
                "name": token.name,
                "symbol": token.symbol,
                "creator": token.creator,
                "launch_venue": token.launch_venue,
                "validation_state": token.validation_state,
                "current_lifecycle": token.current_lifecycle,
                "current_market": token.current_market,
                "source_created_at": _iso(token.source_created_at),
                "first_seen_at": _iso(token.first_seen_at),
                "last_seen_at": _iso(token.last_seen_at),
                "graduated_at": _iso(token.graduated_at),
                "last_source_slot": token.last_source_slot,
                "latest_risk_assessment": (
                    _risk_record_payload(latest_risk) if latest_risk is not None else None
                ),
                "metadata": token.metadata_json,
                "markets": [
                    {
                        "address": market.address,
                        "venue": market.venue,
                        "quote_mint": market.quote_mint,
                        "status": market.status,
                    }
                    for market in markets
                ],
                "lifecycle_history": [
                    {
                        "event_id": str(item.event_id),
                        "lifecycle": item.lifecycle,
                        "validation_state": item.validation_state,
                        "market": item.market_address,
                        "bonding_progress_percent": (
                            str(item.bonding_progress_percent)
                            if item.bonding_progress_percent is not None
                            else None
                        ),
                        "reason": item.reason,
                        "source_signature": item.source_signature,
                        "source_slot": item.source_slot,
                        "source_event_at": _iso(item.source_event_at),
                    }
                    for item in lifecycle
                ],
                "latest_feature_snapshot": (
                    _feature_record_payload(latest_feature) if latest_feature is not None else None
                ),
            }

    async def latest_features(self, mint: str, *, limit: int = 10) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(
                    TokenRecord.network == "solana",
                    TokenRecord.mint == mint,
                )
            )
            if token is None:
                return []
            records = (
                await session.scalars(
                    select(MarketFeatureSnapshotRecord)
                    .where(MarketFeatureSnapshotRecord.token_id == token.id)
                    .order_by(MarketFeatureSnapshotRecord.observed_at.desc())
                    .limit(limit)
                )
            ).all()
            return [_feature_record_payload(record) for record in records]

    async def latest_risk(self, mint: str, *, limit: int = 10) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(
                    TokenRecord.network == "solana",
                    TokenRecord.mint == mint,
                )
            )
            if token is None:
                return []
            records = (
                await session.scalars(
                    select(TokenRiskAssessmentRecord)
                    .where(TokenRiskAssessmentRecord.token_id == token.id)
                    .order_by(TokenRiskAssessmentRecord.assessed_at.desc())
                    .limit(limit)
                )
            ).all()
            return [_risk_record_payload(record) for record in records]

    async def latest_decisions(
        self,
        mint: str,
        *,
        limit: int = 10,
        strategy_key: str | None = None,
    ) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
            )
            if token is None:
                return []
            statement = select(StrategyDecisionRecord).where(
                StrategyDecisionRecord.token_id == token.id
            )
            if strategy_key is not None:
                statement = statement.where(StrategyDecisionRecord.strategy_key == strategy_key)
            records = (
                await session.scalars(
                    statement.order_by(StrategyDecisionRecord.decided_at.desc()).limit(limit)
                )
            ).all()
            return [_decision_record_payload(record) for record in records]

    async def provider_seeds(self) -> dict[str, list[dict[str, Any]]]:
        """Return validated active markets needed to resume ingestion after restart."""
        needed = or_(
            TokenRecord.last_seen_at >= datetime.now(UTC) - timedelta(hours=24),
            TokenRecord.id.in_(
                select(PaperPositionRecord.token_id).where(PaperPositionRecord.status == "open")
            ),
        )
        async with self._sessions() as session:
            latest_id = (
                select(TokenLifecycleEventRecord.event_id)
                .where(TokenLifecycleEventRecord.token_id == TokenRecord.id)
                .order_by(TokenLifecycleEventRecord.source_event_at.desc())
                .limit(1)
                .correlate(TokenRecord)
                .scalar_subquery()
            )
            active_tokens = (
                await session.execute(
                    select(TokenRecord, TokenLifecycleEventRecord)
                    .outerjoin(
                        TokenLifecycleEventRecord, TokenLifecycleEventRecord.event_id == latest_id
                    )
                    .where(
                        needed,
                        TokenRecord.current_lifecycle.in_(
                            [
                                MarketLifecycle.BONDING_CURVE.value,
                                MarketLifecycle.FINAL_STRETCH.value,
                            ]
                        ),
                    )
                )
            ).all()
            curves: list[dict[str, Any]] = []
            for token, latest_lifecycle in active_tokens:
                metadata = token.metadata_json or {}
                curve = metadata.get("bonding_curve")
                initial_reserves = metadata.get("initial_real_token_reserves")
                if not isinstance(curve, str):
                    continue
                curves.append(
                    {
                        "mint": token.mint,
                        "bonding_curve": curve,
                        "initial_real_reserves": initial_reserves
                        if isinstance(initial_reserves, int)
                        else 0,
                        "progress_percent": (
                            latest_lifecycle.bonding_progress_percent
                            if latest_lifecycle is not None
                            else None
                        ),
                        "lifecycle": token.current_lifecycle,
                        "validation_state": token.validation_state,
                        "changed_at": (
                            latest_lifecycle.source_event_at
                            if latest_lifecycle is not None
                            else token.last_seen_at
                        ),
                        "source_slot": token.last_source_slot,
                        "market": token.current_market,
                    }
                )
            pool_records = (
                await session.execute(
                    select(MarketRecord, TokenRecord)
                    .join(TokenRecord, MarketRecord.token_id == TokenRecord.id)
                    .where(MarketRecord.venue == LaunchVenue.PUMP_SWAP.value, needed)
                )
            ).all()
            pools = [
                {
                    "pool": market.address,
                    "mint": token.mint,
                    "quote_mint": market.quote_mint,
                    "lifecycle": token.current_lifecycle,
                    "validation_state": token.validation_state,
                    "changed_at": token.last_seen_at,
                    "source_slot": token.last_source_slot,
                    "market": token.current_market,
                }
                for market, token in pool_records
                if market.quote_mint is not None
            ]
            return {"bonding_curves": curves, "pump_swap_pools": pools}

    async def provider_health(self) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(ProviderHealthRecord).order_by(ProviderHealthRecord.provider)
                )
            ).all()
            return [
                {
                    "provider": record.provider,
                    "state": record.state,
                    "confirmed_capabilities": record.confirmed_capabilities,
                    "unavailable_capabilities": record.unavailable_capabilities,
                    "last_event_at": _iso(record.last_event_at),
                    "last_checked_at": _iso(record.last_checked_at),
                    "reconnect_count": record.reconnect_count,
                    "rate_limited": record.rate_limited,
                    "error_code": record.error_code,
                }
                for record in records
            ]

    async def risk_context(self, mint: str) -> LocalRiskContext | None:
        async with self._sessions() as session:
            token = await session.scalar(
                select(TokenRecord).where(
                    TokenRecord.network == "solana",
                    TokenRecord.mint == mint,
                )
            )
            if token is None:
                return None
            latest_lifecycle = await session.scalar(
                select(TokenLifecycleEventRecord)
                .where(TokenLifecycleEventRecord.token_id == token.id)
                .order_by(TokenLifecycleEventRecord.source_event_at.desc())
                .limit(1)
            )
            creator_tokens: list[TokenRecord] = []
            if token.creator is not None:
                creator_tokens = list(
                    (
                        await session.scalars(
                            select(TokenRecord).where(TokenRecord.creator == token.creator)
                        )
                    ).all()
                )
            early_buys = list(
                (
                    await session.scalars(
                        select(TokenTradeRecord)
                        .where(
                            TokenTradeRecord.token_id == token.id,
                            TokenTradeRecord.side == "buy",
                        )
                        .order_by(TokenTradeRecord.source_event_at, TokenTradeRecord.source_slot)
                        .limit(200)
                    )
                ).all()
            )
            wallet_volume: dict[str, Decimal] = {}
            slot_wallets: dict[int, set[str]] = {}
            for trade in early_buys:
                if trade.wallet is None:
                    continue
                wallet_volume[trade.wallet] = (
                    wallet_volume.get(trade.wallet, Decimal(0)) + trade.quote_amount_raw
                )
                if trade.source_slot is not None:
                    slot_wallets.setdefault(trade.source_slot, set()).add(trade.wallet)
            total_buy_volume = sum(wallet_volume.values(), start=Decimal(0))
            largest_buyer_share = (
                max(wallet_volume.values()) * 100 / total_buy_volume
                if wallet_volume and total_buy_volume > 0
                else None
            )
            metadata = token.metadata_json or {}
            quote_mint = metadata.get("quote_mint")
            return LocalRiskContext(
                mint=token.mint,
                creator=token.creator,
                market=token.current_market,
                quote_mint=quote_mint if isinstance(quote_mint, str) else None,
                lifecycle=MarketLifecycle(token.current_lifecycle),
                validation_state=MarketValidationState(token.validation_state),
                observed_at=(
                    latest_lifecycle.source_event_at
                    if latest_lifecycle is not None
                    else token.last_seen_at
                ),
                source_slot=token.last_source_slot,
                creator_launches=len(creator_tokens),
                creator_graduations=sum(item.graduated_at is not None for item in creator_tokens),
                creator_rejections=sum(
                    item.validation_state == MarketValidationState.REJECTED.value
                    for item in creator_tokens
                ),
                early_unique_buyers=len(wallet_volume),
                largest_early_buyer_share_percent=largest_buyer_share,
                largest_synchronized_buyer_group=max(
                    (len(wallets) for wallets in slot_wallets.values()),
                    default=0,
                ),
            )

    async def global_memecoin_metrics(self, *, as_of: datetime) -> dict[str, Any]:
        as_of = _as_utc(as_of)
        trade_start = as_of - timedelta(minutes=15)
        launch_start = as_of - timedelta(minutes=15)
        graduation_start = as_of - timedelta(minutes=60)
        async with self._sessions() as session:
            launches = await session.scalar(
                select(func.count(TokenRecord.id)).where(
                    TokenRecord.source_created_at >= launch_start,
                    TokenRecord.source_created_at <= as_of,
                )
            )
            graduations = await session.scalar(
                select(func.count(TokenRecord.id)).where(
                    TokenRecord.graduated_at >= graduation_start,
                    TokenRecord.graduated_at <= as_of,
                )
            )
            row = (
                await session.execute(
                    select(
                        func.count(TokenTradeRecord.event_id),
                        func.count(func.distinct(TokenTradeRecord.wallet)),
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        TokenTradeRecord.side == "buy",
                                        TokenTradeRecord.quote_amount_raw,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        TokenTradeRecord.side == "sell",
                                        TokenTradeRecord.quote_amount_raw,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                    ).where(
                        TokenTradeRecord.source_event_at >= trade_start,
                        TokenTradeRecord.source_event_at <= as_of,
                    )
                )
            ).one()
        return {
            "observed_at": as_of.isoformat(),
            "launches_15m": int(launches or 0),
            "graduations_60m": int(graduations or 0),
            "trade_count_15m": int(row[0] or 0),
            "unique_buyers_15m": int(row[1] or 0),
            "buy_volume_15m": str(row[2] or 0),
            "sell_volume_15m": str(row[3] or 0),
        }

    async def save_alpha_filter_snapshot(self, mint: str, payload: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            token = await session.scalar(
                select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
            )
            if token is None:
                return
            metadata = dict(token.metadata_json or {})
            metadata["alpha_filter"] = payload
            token.metadata_json = metadata

    async def alpha_filter_snapshot(self, mint: str) -> dict[str, Any] | None:
        async with self._sessions() as session:
            metadata = await session.scalar(
                select(TokenRecord.metadata_json).where(
                    TokenRecord.network == "solana", TokenRecord.mint == mint
                )
            )
        if not isinstance(metadata, dict):
            return None
        snapshot = metadata.get("alpha_filter")
        return snapshot if isinstance(snapshot, dict) else None

    async def latest_alpha_filter_snapshots(self, *, limit: int = 10) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(TokenRecord.mint, TokenRecord.symbol, TokenRecord.metadata_json)
                    .where(TokenRecord.metadata_json.is_not(None))
                    .order_by(TokenRecord.last_seen_at.desc())
                    .limit(max(limit * 5, limit))
                )
            ).all()
        result: list[dict[str, Any]] = []
        for mint, symbol, metadata in rows:
            snapshot = metadata.get("alpha_filter") if isinstance(metadata, dict) else None
            if not isinstance(snapshot, dict):
                continue
            result.append({"mint": mint, "symbol": symbol, **snapshot})
            if len(result) >= limit:
                break
        return result


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _feature_record_payload(record: MarketFeatureSnapshotRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "trigger_event_id": str(record.trigger_event_id),
        "observed_at": _iso(record.observed_at),
        "lifecycle": record.lifecycle,
        "validation_state": record.validation_state,
        "lifecycle_age_seconds": record.lifecycle_age_seconds,
        "bonding_progress_percent": (
            str(record.bonding_progress_percent)
            if record.bonding_progress_percent is not None
            else None
        ),
        "market": record.market_address,
        "latest_price_raw": (
            str(record.latest_price_raw) if record.latest_price_raw is not None else None
        ),
        "source_slot": record.source_slot,
        "windows": record.windows_json,
    }


def _risk_record_payload(record: TokenRiskAssessmentRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "trigger_event_id": str(record.trigger_event_id),
        "assessed_at": _iso(record.assessed_at),
        "allowed": record.allowed,
        "risk_score": str(record.risk_score) if record.risk_score is not None else None,
        "data_completeness_percent": str(record.data_completeness_percent),
        "hard_reject_reasons": record.hard_reject_reasons,
        "warnings": record.warnings,
        "critical_unknowns": record.critical_unknowns,
        "evidence": record.evidence_json,
        "market": record.market_address,
        "source_slot": record.source_slot,
    }


def _decision_record_payload(record: StrategyDecisionRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "strategy_version_id": str(record.strategy_version_id),
        "strategy_key": record.strategy_key,
        "active_strategy": record.active_strategy,
        "action": record.action,
        "regime": record.regime,
        "risk_event_id": str(record.risk_event_id),
        "feature_event_id": (
            str(record.feature_event_id) if record.feature_event_id is not None else None
        ),
        "decided_at": _iso(record.decided_at),
        "final_score": (str(record.final_score) if record.final_score is not None else None),
        "component_completeness_percent": str(record.component_completeness_percent),
        "components": record.score_components_json,
        "reasons": record.reasons,
        "source_slot": record.source_slot,
    }


async def _portfolio_snapshot(
    session: AsyncSession, portfolio: PaperPortfolioRecord
) -> PortfolioSnapshot:
    open_count = await session.scalar(
        select(func.count())
        .select_from(PaperPositionRecord)
        .where(
            PaperPositionRecord.portfolio_id == portfolio.id,
            PaperPositionRecord.status == "open",
        )
    )
    return PortfolioSnapshot(
        portfolio_id=portfolio.id,
        currency=portfolio.currency,
        initial_cash=portfolio.initial_cash,
        cash_balance=portfolio.cash_balance,
        realized_pnl=portfolio.realized_pnl,
        open_position_count=int(open_count or 0),
    )


def _position_snapshot(position: PaperPositionRecord) -> PositionSnapshot:
    return PositionSnapshot(
        position_id=position.id,
        portfolio_id=position.portfolio_id,
        mint=position.mint,
        strategy_key=position.strategy_key,
        market=position.market_address,
        venue=LaunchVenue(position.venue),
        lifecycle=MarketLifecycle(position.lifecycle),
        token_quantity_raw=position.token_quantity_raw,
        remaining_cost_basis=position.remaining_cost_basis,
        realized_pnl=position.realized_pnl,
        entry_price_raw=position.entry_price_raw,
        peak_price_raw=position.peak_price_raw,
        opened_at=position.opened_at,
        partial_take_profit_taken=position.partial_take_profit_taken,
        execution_mark=position.execution_mark_json,
    )


def _position_record_payload(
    position: PaperPositionRecord,
    token: TokenRecord | None = None,
    *,
    max_mark_age_seconds: int = 5,
) -> dict[str, Any]:
    return {
        "position_id": str(position.id),
        "mint": position.mint,
        "name": token.name if token is not None else None,
        "symbol": token.symbol if token is not None else None,
        "strategy_key": position.strategy_key,
        "market": position.market_address,
        "venue": position.venue,
        "lifecycle": position.lifecycle,
        "status": position.status,
        "token_quantity_raw": str(position.token_quantity_raw),
        "remaining_cost_basis": str(position.remaining_cost_basis),
        "realized_pnl": str(position.realized_pnl),
        "entry_price_raw": str(position.entry_price_raw),
        "peak_price_raw": str(position.peak_price_raw),
        "last_price_raw": str(position.last_price_raw),
        "execution_mark_json": position.execution_mark_json,
        "mark_observed_at": _iso(position.mark_observed_at),
        "execution_mark_valid": bool(
            position.execution_mark_json is not None
            and position.mark_observed_at is not None
            and 0
            <= (datetime.now(UTC) - _as_utc(position.mark_observed_at)).total_seconds()
            <= max_mark_age_seconds
            and Decimal(str(position.execution_mark_json["token_amount_raw"]))
            == position.token_quantity_raw
        ),
        "opened_at": _iso(position.opened_at),
        "closed_at": _iso(position.closed_at),
        "partial_take_profit_taken": position.partial_take_profit_taken,
    }


def _paper_order_record_payload(order: PaperOrderRecord) -> dict[str, Any]:
    return {
        "event_id": str(order.event_id),
        "mint": order.mint,
        "strategy_key": order.strategy_key,
        "side": order.side,
        "status": order.status,
        "position_effect": order.position_effect,
        "rejection_reason": order.rejection_reason,
        "exit_reason": order.exit_reason,
        "requested_portfolio_amount": str(order.requested_portfolio_amount),
        "market": order.market_address,
        "venue": order.venue,
        "lifecycle": order.lifecycle,
        "signal_at": _iso(order.signal_at),
        "decision_at": _iso(order.decision_at),
        "submitted_at": _iso(order.submitted_at),
        "filled_at": _iso(order.filled_at),
        "fill": order.fill_json,
    }
