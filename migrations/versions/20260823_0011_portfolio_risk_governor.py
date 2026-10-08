"""Add atomic paper-position guard and safer sizing defaults.

Revision ID: 20260823_0011
Revises: 20260823_0010
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0011"
down_revision: str | None = "20260823_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_paper_positions_open_portfolio_mint",
        "paper_positions",
        ["portfolio_id", "mint"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.execute(
        sa.text(
            "UPDATE trading_control "
            "SET entries_paused = true, base_position_percent = 1, "
            "max_position_percent = 2, "
            "max_open_positions = 5, take_profit_percent = 25, "
            "trailing_stop_percent = 8"
        )
    )


def downgrade() -> None:
    op.drop_index("uq_paper_positions_open_portfolio_mint", table_name="paper_positions")
