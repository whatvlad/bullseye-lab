"""Add Phase 6 Telegram control-plane state.

Revision ID: 20260822_0007
Revises: 20260822_0006
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0007"
down_revision: str | None = "20260822_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trading_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entries_paused", sa.Boolean(), nullable=False),
        sa.Column("active_strategy_key", sa.String(length=32), nullable=False),
        sa.Column("base_position_percent", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("max_position_percent", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("max_open_positions", sa.Integer(), nullable=False),
        sa.Column("stop_loss_percent", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("take_profit_percent", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("trailing_stop_percent", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("max_holding_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_by_telegram_user_id", sa.BigInteger()),
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
    op.create_table(
        "token_controls",
        sa.Column("mint", sa.String(length=44), nullable=False),
        sa.Column("watchlisted", sa.Boolean(), nullable=False),
        sa.Column("blacklisted", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=256)),
        sa.Column("updated_by_telegram_user_id", sa.BigInteger()),
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
        sa.PrimaryKeyConstraint("mint"),
    )
    op.create_index("ix_token_controls_watchlisted", "token_controls", ["watchlisted"])
    op.create_index("ix_token_controls_blacklisted", "token_controls", ["blacklisted"])


def downgrade() -> None:
    op.drop_index("ix_token_controls_blacklisted", table_name="token_controls")
    op.drop_index("ix_token_controls_watchlisted", table_name="token_controls")
    op.drop_table("token_controls")
    op.drop_table("trading_control")
