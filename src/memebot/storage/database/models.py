from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from memebot.models.market import MarketValidationState


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TokenRecord(TimestampMixin, Base):
    __tablename__ = "tokens"
    __table_args__ = (
        UniqueConstraint("network", "mint", name="uq_tokens_network_mint"),
        Index("ix_tokens_validation_state", "validation_state"),
        Index("ix_tokens_current_lifecycle", "current_lifecycle"),
        Index("ix_tokens_first_seen_at", "first_seen_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    network: Mapped[str] = mapped_column(String(16), nullable=False, default="solana")
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    name: Mapped[str | None] = mapped_column(String(128))
    symbol: Mapped[str | None] = mapped_column(String(32))
    creator: Mapped[str | None] = mapped_column(String(44))
    launch_venue: Mapped[str | None] = mapped_column(String(32))
    validation_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MarketValidationState.DISCOVERED.value,
    )
    current_lifecycle: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
    )
    current_market: Mapped[str | None] = mapped_column(String(44))
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    graduated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_source_slot: Mapped[int | None] = mapped_column(BigInteger)
    risk_allowed: Mapped[bool | None]
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    risk_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_assessment_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    markets: Mapped[list[MarketRecord]] = relationship(
        back_populates="token",
        cascade="all, delete-orphan",
    )


class MarketRecord(TimestampMixin, Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint("network", "address", name="uq_markets_network_address"),
        Index("ix_markets_token_id", "token_id"),
        Index("ix_markets_venue_status", "venue", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    network: Mapped[str] = mapped_column(String(16), nullable=False, default="solana")
    address: Mapped[str] = mapped_column(String(44), nullable=False)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_mint: Mapped[str | None] = mapped_column(String(44))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    token: Mapped[TokenRecord] = relationship(back_populates="markets")


class DomainEventRecord(Base):
    __tablename__ = "domain_events"
    __table_args__ = (
        Index("ix_domain_events_type_source_at", "event_type", "source_event_at"),
        Index("ix_domain_events_provider_ingested_at", "provider", "ingested_at"),
        Index("ix_domain_events_correlation_id", "correlation_id"),
        Index("ix_domain_events_source_signature", "source_signature"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    source_sequence: Mapped[int | None]
    source_signature: Mapped[str | None] = mapped_column(String(128))
    source_slot: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class TokenLifecycleEventRecord(Base):
    __tablename__ = "token_lifecycle_events"
    __table_args__ = (
        Index("ix_token_lifecycle_events_token_source", "token_id", "source_event_at"),
        Index("ix_token_lifecycle_events_lifecycle", "lifecycle"),
        Index("ix_token_lifecycle_events_signature", "source_signature"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    market_address: Mapped[str | None] = mapped_column(String(44))
    quote_mint: Mapped[str | None] = mapped_column(String(44))
    bonding_progress_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    real_token_reserves: Mapped[int | None] = mapped_column(BigInteger)
    real_quote_reserves: Mapped[int | None] = mapped_column(BigInteger)
    reason: Mapped[str | None] = mapped_column(String(512))
    source_signature: Mapped[str | None] = mapped_column(String(128))
    source_slot: Mapped[int | None] = mapped_column(BigInteger)
    source_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TokenTradeRecord(Base):
    __tablename__ = "token_trades"
    __table_args__ = (
        Index("ix_token_trades_token_source", "token_id", "source_event_at"),
        Index("ix_token_trades_signature", "signature"),
        Index("ix_token_trades_market_source", "market_address", "source_event_at"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    signature: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    token_amount_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    quote_amount_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(44), nullable=False)
    quote_mint: Mapped[str | None] = mapped_column(String(44))
    wallet: Mapped[str | None] = mapped_column(String(44))
    market_address: Mapped[str | None] = mapped_column(String(44))
    real_token_reserves: Mapped[int | None] = mapped_column(BigInteger)
    real_quote_reserves: Mapped[int | None] = mapped_column(BigInteger)
    virtual_token_reserves: Mapped[Decimal | None] = mapped_column(Numeric(40, 0))
    virtual_quote_reserves: Mapped[Decimal | None] = mapped_column(Numeric(40, 0))
    source_slot: Mapped[int | None] = mapped_column(BigInteger)
    source_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketFeatureSnapshotRecord(Base):
    __tablename__ = "market_feature_snapshots"
    __table_args__ = (
        Index("ix_feature_snapshots_token_observed", "token_id", "observed_at"),
        Index("ix_feature_snapshots_lifecycle_observed", "lifecycle", "observed_at"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_age_seconds: Mapped[int | None]
    bonding_progress_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    market_address: Mapped[str | None] = mapped_column(String(44))
    latest_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    windows_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    source_slot: Mapped[int | None] = mapped_column(BigInteger)


class TokenRiskAssessmentRecord(Base):
    __tablename__ = "token_risk_assessments"
    __table_args__ = (
        Index("ix_risk_assessments_token_assessed", "token_id", "assessed_at"),
        Index("ix_risk_assessments_allowed_score", "allowed", "risk_score"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    allowed: Mapped[bool | None]
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    data_completeness_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    hard_reject_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    critical_unknowns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    market_address: Mapped[str | None] = mapped_column(String(44))
    source_slot: Mapped[int | None] = mapped_column(BigInteger)


class StrategyConfigurationRecord(Base):
    __tablename__ = "strategy_configurations"
    __table_args__ = (
        UniqueConstraint("strategy_key", "version", name="uq_strategy_key_version"),
        Index("ix_strategy_configurations_enabled_active", "enabled", "active_for_execution"),
    )

    version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False)
    active_for_execution: Mapped[bool] = mapped_column(nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StrategyDecisionRecord(Base):
    __tablename__ = "strategy_decisions"
    __table_args__ = (
        Index("ix_strategy_decisions_token_decided", "token_id", "decided_at"),
        Index("ix_strategy_decisions_strategy_action", "strategy_key", "action"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("strategy_configurations.version_id"),
        nullable=False,
    )
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    active_strategy: Mapped[bool] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    regime: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    feature_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    component_completeness_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    score_components_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_slot: Mapped[int | None] = mapped_column(BigInteger)


class PaperPortfolioRecord(TimestampMixin, Base):
    __tablename__ = "paper_portfolios"
    __table_args__ = (Index("ix_paper_portfolios_active", "active"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(30, 8), nullable=False, default=Decimal(0)
    )
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class ExperimentRunRecord(TimestampMixin, Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        UniqueConstraint("name", name="uq_experiment_runs_name"),
        UniqueConstraint("portfolio_id", name="uq_experiment_runs_portfolio"),
        Index("ix_experiment_runs_status_started", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("strategy_configurations.version_id"), nullable=False
    )
    application_version: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class PaperPositionRecord(TimestampMixin, Base):
    __tablename__ = "paper_positions"
    __table_args__ = (
        Index("ix_paper_positions_portfolio_status", "portfolio_id", "status"),
        Index("ix_paper_positions_mint_status", "mint", "status"),
        Index(
            "uq_paper_positions_open_portfolio_mint",
            "portfolio_id",
            "mint",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    market_address: Mapped[str] = mapped_column(String(44), nullable=False)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    token_quantity_raw: Mapped[Decimal] = mapped_column(Numeric(40, 8), nullable=False)
    remaining_cost_basis: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(30, 8), nullable=False, default=Decimal(0)
    )
    entry_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    peak_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    last_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    partial_take_profit_taken: Mapped[bool] = mapped_column(nullable=False, default=False)
    mark_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_mark_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class PaperOrderRecord(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (
        Index("ix_paper_orders_portfolio_created", "portfolio_id", "created_at"),
        Index("ix_paper_orders_mint_status", "mint", "status"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("domain_events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("paper_portfolios.id"), nullable=False
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    trigger_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    position_effect: Mapped[str] = mapped_column(String(24), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(512))
    exit_reason: Mapped[str | None] = mapped_column(String(64))
    market_address: Mapped[str | None] = mapped_column(String(44))
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_portfolio_amount: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fill_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PendingPaperActionRecord(TimestampMixin, Base):
    __tablename__ = "pending_paper_actions"
    __table_args__ = (
        Index("ix_pending_paper_actions_status_expiry", "status", "expires_at"),
        Index("ix_pending_paper_actions_mint_status", "mint", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("paper_portfolios.id"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    decision_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    requested_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    reason: Mapped[str | None] = mapped_column(String(128))


class TradingControlRecord(TimestampMixin, Base):
    __tablename__ = "trading_control"

    id: Mapped[int] = mapped_column(primary_key=True)
    entries_paused: Mapped[bool] = mapped_column(nullable=False, default=False)
    active_strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    base_position_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    max_position_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    max_open_positions: Mapped[int] = mapped_column(nullable=False)
    stop_loss_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    take_profit_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    trailing_stop_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    max_holding_seconds: Mapped[int] = mapped_column(nullable=False)
    # Telegram-set SOL tier sizes (sol_tiers mode); NULL keeps the .env defaults.
    sol_tier_small: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    sol_tier_medium: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    sol_tier_large: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    updated_by_telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)


class TokenControlRecord(TimestampMixin, Base):
    __tablename__ = "token_controls"
    __table_args__ = (
        Index("ix_token_controls_watchlisted", "watchlisted"),
        Index("ix_token_controls_blacklisted", "blacklisted"),
    )

    mint: Mapped[str] = mapped_column(String(44), primary_key=True)
    watchlisted: Mapped[bool] = mapped_column(nullable=False, default=False)
    blacklisted: Mapped[bool] = mapped_column(nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(String(256))
    updated_by_telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)


class DecisionOutcomeRecord(TimestampMixin, Base):
    __tablename__ = "decision_outcomes"
    __table_args__ = (
        Index("ix_decision_outcomes_token_decided", "token_id", "decided_at"),
        Index("ix_decision_outcomes_strategy_action", "strategy_key", "action"),
        Index("ix_decision_outcomes_execution_status", "execution_status"),
    )

    decision_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("strategy_decisions.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    active_strategy: Mapped[bool] = mapped_column(nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    baseline_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    baseline_market: Mapped[str | None] = mapped_column(String(44))
    baseline_lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    score_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    order_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    execution_rejection_reason: Mapped[str | None] = mapped_column(String(512))
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    maximum_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    minimum_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    post_decision_ath_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfe_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    mae_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    horizon_returns_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    graduated: Mapped[bool] = mapped_column(nullable=False, default=False)
    graduated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liquidity_collapsed: Mapped[bool] = mapped_column(nullable=False, default=False)
    liquidity_collapsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TradeOutcomeRecord(TimestampMixin, Base):
    __tablename__ = "trade_outcomes"
    __table_args__ = (
        Index("ix_trade_outcomes_strategy_status", "strategy_key", "status"),
        Index("ix_trade_outcomes_token_entry", "token_id", "entry_at"),
    )

    position_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("paper_positions.id", ondelete="CASCADE"), primary_key=True
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("paper_portfolios.id"), nullable=False
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_decision_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    entry_order_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("paper_orders.event_id"), unique=True, nullable=False
    )
    entry_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    feature_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    score_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_entry_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    actual_entry_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    entry_cost_portfolio: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    entry_fees_portfolio: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    entry_slippage_bps: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entry_latency_ms: Mapped[int] = mapped_column(nullable=False)
    highest_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    lowest_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    mfe_percent: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    mae_percent: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    exit_order_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_reason: Mapped[str | None] = mapped_column(String(64))
    expected_exit_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    actual_exit_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(30, 8))
    pnl_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    holding_seconds: Mapped[int | None]
    post_exit_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    graduated: Mapped[bool] = mapped_column(nullable=False, default=False)
    liquidity_collapsed: Mapped[bool] = mapped_column(nullable=False, default=False)


class WalletRecord(TimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (
        Index("ix_wallets_seeded", "seeded"),
        Index("ix_wallets_status_alpha", "status", "latest_alpha_score"),
    )

    address: Mapped[str] = mapped_column(String(44), primary_key=True)
    seeded: Mapped[bool] = mapped_column(nullable=False, default=False)
    label: Mapped[str | None] = mapped_column(String(64))
    discovery_source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_trade_count: Mapped[int] = mapped_column(nullable=False, default=0)
    latest_alpha_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="insufficient")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metrics_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WalletTradeObservationRecord(Base):
    __tablename__ = "wallet_trade_observations"
    __table_args__ = (
        Index("ix_wallet_trades_wallet_time", "wallet_address", "occurred_at"),
        Index("ix_wallet_trades_token_time", "token_id", "occurred_at"),
    )

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("token_trades.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    wallet_address: Mapped[str] = mapped_column(
        String(44), ForeignKey("wallets.address", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    token_amount_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    quote_amount_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    source_slot: Mapped[int | None] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WalletTokenOutcomeRecord(TimestampMixin, Base):
    __tablename__ = "wallet_token_outcomes"
    __table_args__ = (
        UniqueConstraint("wallet_address", "token_id", name="uq_wallet_token_outcome"),
        Index("ix_wallet_outcomes_wallet_entry", "wallet_address", "first_buy_at"),
        Index("ix_wallet_outcomes_token_entry", "token_id", "first_buy_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address: Mapped[str] = mapped_column(
        String(44), ForeignKey("wallets.address", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    mint: Mapped[str] = mapped_column(String(44), nullable=False)
    first_buy_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_buy_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    last_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(50, 24))
    entry_delay_seconds: Mapped[int | None]
    early_entry: Mapped[bool | None]
    buy_count: Mapped[int] = mapped_column(nullable=False, default=0)
    sell_count: Mapped[int] = mapped_column(nullable=False, default=0)
    total_token_bought_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    total_quote_spent_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    total_token_sold_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    total_quote_received_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    remaining_token_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    remaining_cost_quote_raw: Mapped[Decimal] = mapped_column(Numeric(40, 0), nullable=False)
    realized_pnl_quote_raw: Mapped[Decimal] = mapped_column(Numeric(40, 8), nullable=False)
    realized_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(50, 8))
    highest_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    lowest_price_raw: Mapped[Decimal] = mapped_column(Numeric(50, 24), nullable=False)
    mfe_percent: Mapped[Decimal] = mapped_column(Numeric(50, 8), nullable=False)
    mae_percent: Mapped[Decimal] = mapped_column(Numeric(50, 8), nullable=False)
    first_expansion_50_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lead_seconds_before_50_percent: Mapped[int | None]
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    holding_seconds: Mapped[int | None]
    graduated: Mapped[bool] = mapped_column(nullable=False, default=False)
    liquidity_collapsed: Mapped[bool] = mapped_column(nullable=False, default=False)


class ProviderHealthRecord(TimestampMixin, Base):
    __tablename__ = "provider_health"
    __table_args__ = (Index("ix_provider_health_state", "state"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unavailable_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reconnect_count: Mapped[int] = mapped_column(nullable=False, default=0)
    average_message_latency_ms: Mapped[float | None]
    rate_limited: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
