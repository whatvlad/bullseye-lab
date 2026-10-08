"""Add Phase 4 versioned strategies and immutable decisions.

Revision ID: 20260822_0005
Revises: 20260822_0004
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0005"
down_revision: str | None = "20260822_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_configurations",
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("active_for_execution", sa.Boolean(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("version_id"),
        sa.UniqueConstraint("strategy_key", "version", name="uq_strategy_key_version"),
    )
    op.create_index(
        "ix_strategy_configurations_enabled_active",
        "strategy_configurations",
        ["enabled", "active_for_execution"],
    )
    op.create_table(
        "strategy_decisions",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_version_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("active_strategy", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("regime", sa.String(length=32), nullable=False),
        sa.Column("risk_event_id", sa.Uuid(), nullable=False),
        sa.Column("feature_event_id", sa.Uuid()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final_score", sa.Numeric(precision=6, scale=2)),
        sa.Column(
            "component_completeness_percent",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
        ),
        sa.Column("score_components_json", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("source_slot", sa.BigInteger()),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_configurations.version_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_strategy_decisions_token_decided",
        "strategy_decisions",
        ["token_id", "decided_at"],
    )
    op.create_index(
        "ix_strategy_decisions_strategy_action",
        "strategy_decisions",
        ["strategy_key", "action"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_decisions_strategy_action", table_name="strategy_decisions")
    op.drop_index("ix_strategy_decisions_token_decided", table_name="strategy_decisions")
    op.drop_table("strategy_decisions")
    op.drop_index(
        "ix_strategy_configurations_enabled_active",
        table_name="strategy_configurations",
    )
    op.drop_table("strategy_configurations")
