"""Create Phase 0 core tables.

Revision ID: 20260822_0001
Revises: None
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("network", sa.String(length=16), nullable=False),
        sa.Column("mint", sa.String(length=44), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("creator", sa.String(length=44), nullable=True),
        sa.Column("launch_venue", sa.String(length=32), nullable=True),
        sa.Column("validation_state", sa.String(length=32), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("network", "mint", name="uq_tokens_network_mint"),
    )
    op.create_index("ix_tokens_first_seen_at", "tokens", ["first_seen_at"])
    op.create_index("ix_tokens_validation_state", "tokens", ["validation_state"])

    op.create_table(
        "markets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("network", sa.String(length=16), nullable=False),
        sa.Column("address", sa.String(length=44), nullable=False),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("quote_mint", sa.String(length=44), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("network", "address", name="uq_markets_network_address"),
    )
    op.create_index("ix_markets_token_id", "markets", ["token_id"])
    op.create_index("ix_markets_venue_status", "markets", ["venue", "status"])

    op.create_table(
        "domain_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("source_sequence", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_domain_events_correlation_id", "domain_events", ["correlation_id"])
    op.create_index(
        "ix_domain_events_provider_ingested_at",
        "domain_events",
        ["provider", "ingested_at"],
    )
    op.create_index(
        "ix_domain_events_type_source_at",
        "domain_events",
        ["event_type", "source_event_at"],
    )

    op.create_table(
        "provider_health",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("confirmed_capabilities", sa.JSON(), nullable=False),
        sa.Column("unavailable_capabilities", sa.JSON(), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconnect_count", sa.Integer(), nullable=False),
        sa.Column("average_message_latency_ms", sa.Float(), nullable=True),
        sa.Column("rate_limited", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
    )
    op.create_index("ix_provider_health_state", "provider_health", ["state"])


def downgrade() -> None:
    op.drop_index("ix_provider_health_state", table_name="provider_health")
    op.drop_table("provider_health")
    op.drop_index("ix_domain_events_type_source_at", table_name="domain_events")
    op.drop_index("ix_domain_events_provider_ingested_at", table_name="domain_events")
    op.drop_index("ix_domain_events_correlation_id", table_name="domain_events")
    op.drop_table("domain_events")
    op.drop_index("ix_markets_venue_status", table_name="markets")
    op.drop_index("ix_markets_token_id", table_name="markets")
    op.drop_table("markets")
    op.drop_index("ix_tokens_validation_state", table_name="tokens")
    op.drop_index("ix_tokens_first_seen_at", table_name="tokens")
    op.drop_table("tokens")
