"""Add isolated paper experiment runs.

Revision ID: 20260823_0014
Revises: 20260823_0013
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0014"
down_revision: str | None = "20260823_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(length=32), nullable=False),
        sa.Column("strategy_version_id", sa.Uuid(), nullable=False),
        sa.Column("application_version", sa.String(length=32), nullable=False),
        sa.Column("configuration_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["paper_portfolios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_configurations.version_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_experiment_runs_name"),
        sa.UniqueConstraint("portfolio_id", name="uq_experiment_runs_portfolio"),
    )
    op.create_index(
        "ix_experiment_runs_status_started",
        "experiment_runs",
        ["status", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_experiment_runs_status_started", table_name="experiment_runs")
    op.drop_table("experiment_runs")
