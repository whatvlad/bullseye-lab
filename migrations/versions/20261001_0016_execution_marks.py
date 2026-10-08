"""Keep executable position marks separate from stream excursions."""

import sqlalchemy as sa
from alembic import op

revision = "20261001_0016"
down_revision = "20260913_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_positions", sa.Column("execution_mark_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_positions", "execution_mark_json")
