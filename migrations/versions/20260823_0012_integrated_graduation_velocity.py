"""Retire standalone graduation preset and supersede Phase 4 strategy versions.

Revision ID: 20260823_0012
Revises: 20260823_0011
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0012"
down_revision: str | None = "20260823_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE strategy_configurations SET enabled = false "
            "WHERE strategy_key IN "
            "('conservative', 'balanced', 'aggressive', 'graduation_velocity_v1')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE strategy_configurations SET enabled = true "
            "WHERE version = 1 AND strategy_key IN "
            "('conservative', 'balanced', 'aggressive', 'graduation_velocity_v1')"
        )
    )
