"""Add Phase 5 paper portfolios, orders, fills, and positions.

Revision ID: 20260822_0006
Revises: 20260822_0005
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0006"
down_revision: str | None = "20260822_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "token_trades",
        sa.Column("virtual_token_reserves", sa.Numeric(precision=40, scale=0)),
    )
    op.create_table(
        "paper_portfolios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("initial_cash", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("cash_balance", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_portfolios_active", "paper_portfolios", ["active"])
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(length=44), nullable=False),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("market_address", sa.String(length=44), nullable=False),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("token_quantity_raw", sa.Numeric(precision=40, scale=8), nullable=False),
        sa.Column("remaining_cost_basis", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("entry_price_raw", sa.Numeric(precision=50, scale=24), nullable=False),
        sa.Column("peak_price_raw", sa.Numeric(precision=50, scale=24), nullable=False),
        sa.Column("last_price_raw", sa.Numeric(precision=50, scale=24), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("partial_take_profit_taken", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["paper_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_paper_positions_portfolio_status",
        "paper_positions",
        ["portfolio_id", "status"],
    )
    op.create_index("ix_paper_positions_mint_status", "paper_positions", ["mint", "status"])
    op.create_table(
        "paper_orders",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(length=44), nullable=False),
        sa.Column("trigger_event_id", sa.Uuid(), nullable=False),
        sa.Column("decision_event_id", sa.Uuid()),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("position_effect", sa.String(length=24), nullable=False),
        sa.Column("rejection_reason", sa.String(length=512)),
        sa.Column("exit_reason", sa.String(length=64)),
        sa.Column("market_address", sa.String(length=44)),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("requested_portfolio_amount", sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column("signal_at", sa.DateTime(timezone=True)),
        sa.Column("decision_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("filled_at", sa.DateTime(timezone=True)),
        sa.Column("fill_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["paper_portfolios.id"]),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_paper_orders_portfolio_created",
        "paper_orders",
        ["portfolio_id", "created_at"],
    )
    op.create_index("ix_paper_orders_mint_status", "paper_orders", ["mint", "status"])


def downgrade() -> None:
    op.drop_index("ix_paper_orders_mint_status", table_name="paper_orders")
    op.drop_index("ix_paper_orders_portfolio_created", table_name="paper_orders")
    op.drop_table("paper_orders")
    op.drop_index("ix_paper_positions_mint_status", table_name="paper_positions")
    op.drop_index("ix_paper_positions_portfolio_status", table_name="paper_positions")
    op.drop_table("paper_positions")
    op.drop_index("ix_paper_portfolios_active", table_name="paper_portfolios")
    op.drop_table("paper_portfolios")
    op.drop_column("token_trades", "virtual_token_reserves")
