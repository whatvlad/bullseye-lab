"""Add Phase 1 discovery and lifecycle state.

Revision ID: 20260822_0002
Revises: 20260822_0001
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0002"
down_revision: str | None = "20260822_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tokens",
        sa.Column(
            "current_lifecycle",
            sa.String(length=32),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.add_column("tokens", sa.Column("current_market", sa.String(length=44)))
    op.add_column(
        "tokens",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column("tokens", sa.Column("graduated_at", sa.DateTime(timezone=True)))
    op.add_column("tokens", sa.Column("last_source_slot", sa.BigInteger()))
    op.create_index("ix_tokens_current_lifecycle", "tokens", ["current_lifecycle"])

    op.add_column("domain_events", sa.Column("source_signature", sa.String(length=128)))
    op.add_column("domain_events", sa.Column("source_slot", sa.BigInteger()))
    op.create_index(
        "ix_domain_events_source_signature",
        "domain_events",
        ["source_signature"],
    )

    op.create_table(
        "token_lifecycle_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("validation_state", sa.String(length=32), nullable=False),
        sa.Column("market_address", sa.String(length=44)),
        sa.Column("quote_mint", sa.String(length=44)),
        sa.Column("bonding_progress_percent", sa.Numeric(precision=6, scale=3)),
        sa.Column("real_token_reserves", sa.BigInteger()),
        sa.Column("real_quote_reserves", sa.BigInteger()),
        sa.Column("reason", sa.String(length=512)),
        sa.Column("source_signature", sa.String(length=128)),
        sa.Column("source_slot", sa.BigInteger()),
        sa.Column("source_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["domain_events.event_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_token_lifecycle_events_token_source",
        "token_lifecycle_events",
        ["token_id", "source_event_at"],
    )
    op.create_index(
        "ix_token_lifecycle_events_lifecycle",
        "token_lifecycle_events",
        ["lifecycle"],
    )
    op.create_index(
        "ix_token_lifecycle_events_signature",
        "token_lifecycle_events",
        ["source_signature"],
    )


def downgrade() -> None:
    op.drop_index("ix_token_lifecycle_events_signature", table_name="token_lifecycle_events")
    op.drop_index("ix_token_lifecycle_events_lifecycle", table_name="token_lifecycle_events")
    op.drop_index("ix_token_lifecycle_events_token_source", table_name="token_lifecycle_events")
    op.drop_table("token_lifecycle_events")
    op.drop_index("ix_domain_events_source_signature", table_name="domain_events")
    op.drop_column("domain_events", "source_slot")
    op.drop_column("domain_events", "source_signature")
    op.drop_index("ix_tokens_current_lifecycle", table_name="tokens")
    op.drop_column("tokens", "graduated_at")
    op.drop_column("tokens", "last_source_slot")
    op.drop_column("tokens", "last_seen_at")
    op.drop_column("tokens", "current_market")
    op.drop_column("tokens", "current_lifecycle")
