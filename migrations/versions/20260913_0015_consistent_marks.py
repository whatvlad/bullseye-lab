"""Record the event-time watermark of position valuations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0015"
down_revision: str | None = "20260823_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "paper_positions", sa.Column("mark_observed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("trade_outcomes", sa.Column("post_exit_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trade_outcomes", "post_exit_json")
    op.drop_column("paper_positions", "mark_observed_at")
