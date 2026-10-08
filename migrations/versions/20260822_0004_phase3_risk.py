"""Add Phase 3 evidence-backed token risk assessments.

Revision ID: 20260822_0004
Revises: 20260822_0003
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0004"
down_revision: str | None = "20260822_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tokens", sa.Column("risk_allowed", sa.Boolean()))
    op.add_column("tokens", sa.Column("risk_score", sa.Numeric(precision=6, scale=2)))
    op.add_column("tokens", sa.Column("risk_assessed_at", sa.DateTime(timezone=True)))
    op.add_column("tokens", sa.Column("risk_assessment_event_id", sa.Uuid()))

    op.create_table(
        "token_risk_assessments",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_event_id", sa.Uuid(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allowed", sa.Boolean()),
        sa.Column("risk_score", sa.Numeric(precision=6, scale=2)),
        sa.Column(
            "data_completeness_percent",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
        ),
        sa.Column("hard_reject_reasons", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("critical_unknowns", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("market_address", sa.String(length=44)),
        sa.Column("source_slot", sa.BigInteger()),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_risk_assessments_token_assessed",
        "token_risk_assessments",
        ["token_id", "assessed_at"],
    )
    op.create_index(
        "ix_risk_assessments_allowed_score",
        "token_risk_assessments",
        ["allowed", "risk_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_risk_assessments_allowed_score", table_name="token_risk_assessments")
    op.drop_index("ix_risk_assessments_token_assessed", table_name="token_risk_assessments")
    op.drop_table("token_risk_assessments")
    op.drop_column("tokens", "risk_assessment_event_id")
    op.drop_column("tokens", "risk_assessed_at")
    op.drop_column("tokens", "risk_score")
    op.drop_column("tokens", "risk_allowed")
