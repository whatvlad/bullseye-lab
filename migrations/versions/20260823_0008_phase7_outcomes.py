"""Add Phase 7 decision and trade outcome tracking.

Revision ID: 20260823_0008
Revises: 20260822_0007
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0008"
down_revision: str | None = "20260822_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_outcomes",
        sa.Column("decision_event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(44), nullable=False),
        sa.Column("strategy_key", sa.String(32), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("active_strategy", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_price_raw", sa.Numeric(50, 24)),
        sa.Column("baseline_market", sa.String(44)),
        sa.Column("baseline_lifecycle", sa.String(32), nullable=False),
        sa.Column("feature_snapshot_json", sa.JSON()),
        sa.Column("risk_snapshot_json", sa.JSON()),
        sa.Column("score_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("decision_reasons", sa.JSON(), nullable=False),
        sa.Column("execution_status", sa.String(32), nullable=False),
        sa.Column("order_event_id", sa.Uuid()),
        sa.Column("execution_rejection_reason", sa.String(512)),
        sa.Column("last_observed_at", sa.DateTime(timezone=True)),
        sa.Column("last_price_raw", sa.Numeric(50, 24)),
        sa.Column("maximum_price_raw", sa.Numeric(50, 24)),
        sa.Column("minimum_price_raw", sa.Numeric(50, 24)),
        sa.Column("post_decision_ath_at", sa.DateTime(timezone=True)),
        sa.Column("mfe_percent", sa.Numeric(18, 8)),
        sa.Column("mae_percent", sa.Numeric(18, 8)),
        sa.Column("horizon_returns_json", sa.JSON(), nullable=False),
        sa.Column("graduated", sa.Boolean(), nullable=False),
        sa.Column("graduated_at", sa.DateTime(timezone=True)),
        sa.Column("liquidity_collapsed", sa.Boolean(), nullable=False),
        sa.Column("liquidity_collapsed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["decision_event_id"], ["strategy_decisions.event_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("decision_event_id"),
    )
    op.create_index(
        "ix_decision_outcomes_token_decided", "decision_outcomes", ["token_id", "decided_at"]
    )
    op.create_index(
        "ix_decision_outcomes_strategy_action", "decision_outcomes", ["strategy_key", "action"]
    )
    op.create_index(
        "ix_decision_outcomes_execution_status", "decision_outcomes", ["execution_status"]
    )
    op.create_table(
        "trade_outcomes",
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(44), nullable=False),
        sa.Column("strategy_key", sa.String(32), nullable=False),
        sa.Column("entry_decision_event_id", sa.Uuid()),
        sa.Column("entry_order_event_id", sa.Uuid(), nullable=False),
        sa.Column("entry_reasons", sa.JSON(), nullable=False),
        sa.Column("feature_snapshot_json", sa.JSON()),
        sa.Column("risk_snapshot_json", sa.JSON()),
        sa.Column("score_snapshot_json", sa.JSON()),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_entry_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("actual_entry_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("entry_cost_portfolio", sa.Numeric(30, 8), nullable=False),
        sa.Column("entry_fees_portfolio", sa.Numeric(30, 8), nullable=False),
        sa.Column("entry_slippage_bps", sa.Numeric(18, 8), nullable=False),
        sa.Column("entry_latency_ms", sa.Integer(), nullable=False),
        sa.Column("highest_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("lowest_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("mfe_percent", sa.Numeric(18, 8), nullable=False),
        sa.Column("mae_percent", sa.Numeric(18, 8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("exit_order_event_id", sa.Uuid()),
        sa.Column("exit_at", sa.DateTime(timezone=True)),
        sa.Column("exit_reason", sa.String(64)),
        sa.Column("expected_exit_price_raw", sa.Numeric(50, 24)),
        sa.Column("actual_exit_price_raw", sa.Numeric(50, 24)),
        sa.Column("realized_pnl", sa.Numeric(30, 8)),
        sa.Column("pnl_percent", sa.Numeric(18, 8)),
        sa.Column("holding_seconds", sa.Integer()),
        sa.Column("graduated", sa.Boolean(), nullable=False),
        sa.Column("liquidity_collapsed", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["position_id"], ["paper_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["paper_portfolios.id"]),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"]),
        sa.ForeignKeyConstraint(["entry_order_event_id"], ["paper_orders.event_id"]),
        sa.PrimaryKeyConstraint("position_id"),
        sa.UniqueConstraint("entry_order_event_id"),
    )
    op.create_index(
        "ix_trade_outcomes_strategy_status", "trade_outcomes", ["strategy_key", "status"]
    )
    op.create_index("ix_trade_outcomes_token_entry", "trade_outcomes", ["token_id", "entry_at"])


def downgrade() -> None:
    op.drop_index("ix_trade_outcomes_token_entry", table_name="trade_outcomes")
    op.drop_index("ix_trade_outcomes_strategy_status", table_name="trade_outcomes")
    op.drop_table("trade_outcomes")
    op.drop_index("ix_decision_outcomes_execution_status", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_strategy_action", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_token_decided", table_name="decision_outcomes")
    op.drop_table("decision_outcomes")
