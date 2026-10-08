"""Add persistent pending paper actions.

Revision ID: 20260823_0010
Revises: 20260823_0009
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0010"
down_revision: str | None = "20260823_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pending_paper_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("mint", sa.String(44), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decision_event_id", sa.Uuid()),
        sa.Column("requested_by_user_id", sa.BigInteger()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("completion_event_id", sa.Uuid()),
        sa.Column("reason", sa.String(128)),
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
        sa.ForeignKeyConstraint(["portfolio_id"], ["paper_portfolios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_paper_actions_status_expiry",
        "pending_paper_actions",
        ["status", "expires_at"],
    )
    op.create_index(
        "ix_pending_paper_actions_mint_status",
        "pending_paper_actions",
        ["mint", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_paper_actions_mint_status", table_name="pending_paper_actions")
    op.drop_index("ix_pending_paper_actions_status_expiry", table_name="pending_paper_actions")
    op.drop_table("pending_paper_actions")
