"""Add Phase 8 wallet intelligence.

Revision ID: 20260823_0009
Revises: 20260823_0008
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0009"
down_revision: str | None = "20260823_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("address", sa.String(44), nullable=False),
        sa.Column("seeded", sa.Boolean(), nullable=False),
        sa.Column("label", sa.String(64)),
        sa.Column("discovery_source", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_trade_count", sa.Integer(), nullable=False),
        sa.Column("latest_alpha_score", sa.Numeric(6, 2)),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("metrics_json", sa.JSON()),
        sa.Column("metrics_calculated_at", sa.DateTime(timezone=True)),
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
        sa.PrimaryKeyConstraint("address"),
    )
    op.create_index("ix_wallets_seeded", "wallets", ["seeded"])
    op.create_index("ix_wallets_status_alpha", "wallets", ["status", "latest_alpha_score"])
    op.create_table(
        "wallet_trade_observations",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_address", sa.String(44), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(44), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("token_amount_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("quote_amount_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("source_slot", sa.BigInteger()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["token_trades.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_address"], ["wallets.address"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_wallet_trades_wallet_time",
        "wallet_trade_observations",
        ["wallet_address", "occurred_at"],
    )
    op.create_index(
        "ix_wallet_trades_token_time", "wallet_trade_observations", ["token_id", "occurred_at"]
    )
    op.create_table(
        "wallet_token_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wallet_address", sa.String(44), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(44), nullable=False),
        sa.Column("first_buy_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_buy_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("entry_delay_seconds", sa.Integer()),
        sa.Column("early_entry", sa.Boolean()),
        sa.Column("buy_count", sa.Integer(), nullable=False),
        sa.Column("sell_count", sa.Integer(), nullable=False),
        sa.Column("total_token_bought_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("total_quote_spent_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("total_token_sold_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("total_quote_received_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("remaining_token_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("remaining_cost_quote_raw", sa.Numeric(40, 0), nullable=False),
        sa.Column("realized_pnl_quote_raw", sa.Numeric(40, 8), nullable=False),
        sa.Column("realized_return_percent", sa.Numeric(18, 8)),
        sa.Column("highest_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("lowest_price_raw", sa.Numeric(50, 24), nullable=False),
        sa.Column("mfe_percent", sa.Numeric(18, 8), nullable=False),
        sa.Column("mae_percent", sa.Numeric(18, 8), nullable=False),
        sa.Column("first_expansion_50_at", sa.DateTime(timezone=True)),
        sa.Column("lead_seconds_before_50_percent", sa.Integer()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
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
        sa.ForeignKeyConstraint(["wallet_address"], ["wallets.address"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wallet_address", "token_id", name="uq_wallet_token_outcome"),
    )
    op.create_index(
        "ix_wallet_outcomes_wallet_entry",
        "wallet_token_outcomes",
        ["wallet_address", "first_buy_at"],
    )
    op.create_index(
        "ix_wallet_outcomes_token_entry", "wallet_token_outcomes", ["token_id", "first_buy_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_wallet_outcomes_token_entry", table_name="wallet_token_outcomes")
    op.drop_index("ix_wallet_outcomes_wallet_entry", table_name="wallet_token_outcomes")
    op.drop_table("wallet_token_outcomes")
    op.drop_index("ix_wallet_trades_token_time", table_name="wallet_trade_observations")
    op.drop_index("ix_wallet_trades_wallet_time", table_name="wallet_trade_observations")
    op.drop_table("wallet_trade_observations")
    op.drop_index("ix_wallets_status_alpha", table_name="wallets")
    op.drop_index("ix_wallets_seeded", table_name="wallets")
    op.drop_table("wallets")
