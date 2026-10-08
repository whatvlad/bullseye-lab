"""Add Phase 2 trades and rolling feature snapshots.

Revision ID: 20260822_0003
Revises: 20260822_0002
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0003"
down_revision: str | None = "20260822_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "token_trades",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("signature", sa.String(length=128), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("token_amount_raw", sa.Numeric(precision=40, scale=0), nullable=False),
        sa.Column("quote_amount_raw", sa.Numeric(precision=40, scale=0), nullable=False),
        sa.Column("price_raw", sa.Numeric(precision=50, scale=24), nullable=False),
        sa.Column("quote_asset", sa.String(length=44), nullable=False),
        sa.Column("quote_mint", sa.String(length=44)),
        sa.Column("wallet", sa.String(length=44)),
        sa.Column("market_address", sa.String(length=44)),
        sa.Column("real_token_reserves", sa.BigInteger()),
        sa.Column("real_quote_reserves", sa.BigInteger()),
        sa.Column("virtual_quote_reserves", sa.Numeric(precision=40, scale=0)),
        sa.Column("source_slot", sa.BigInteger()),
        sa.Column("source_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_token_trades_token_source", "token_trades", ["token_id", "source_event_at"])
    op.create_index("ix_token_trades_signature", "token_trades", ["signature"])
    op.create_index(
        "ix_token_trades_market_source",
        "token_trades",
        ["market_address", "source_event_at"],
    )

    op.create_table(
        "market_feature_snapshots",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_event_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("validation_state", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_age_seconds", sa.Integer()),
        sa.Column("bonding_progress_percent", sa.Numeric(precision=6, scale=3)),
        sa.Column("market_address", sa.String(length=44)),
        sa.Column("latest_price_raw", sa.Numeric(precision=50, scale=24)),
        sa.Column("windows_json", sa.JSON(), nullable=False),
        sa.Column("source_slot", sa.BigInteger()),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_feature_snapshots_token_observed",
        "market_feature_snapshots",
        ["token_id", "observed_at"],
    )
    op.create_index(
        "ix_feature_snapshots_lifecycle_observed",
        "market_feature_snapshots",
        ["lifecycle", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feature_snapshots_lifecycle_observed",
        table_name="market_feature_snapshots",
    )
    op.drop_index(
        "ix_feature_snapshots_token_observed",
        table_name="market_feature_snapshots",
    )
    op.drop_table("market_feature_snapshots")
    op.drop_index("ix_token_trades_market_source", table_name="token_trades")
    op.drop_index("ix_token_trades_signature", table_name="token_trades")
    op.drop_index("ix_token_trades_token_source", table_name="token_trades")
    op.drop_table("token_trades")
