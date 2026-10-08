"""Add current valuation state for tracked-wallet token outcomes.

Revision ID: 20260823_0013
Revises: 20260823_0012
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0013"
down_revision: str | None = "20260823_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "wallet_token_outcomes",
        sa.Column("last_price_raw", sa.Numeric(50, 24), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE wallet_token_outcomes SET last_price_raw = first_buy_price_raw "
            "WHERE last_price_raw IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("wallet_token_outcomes", "last_price_raw")
