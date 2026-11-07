"""Operator-set SOL tier sizes (Telegram); NULL keeps the .env defaults."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0018"
down_revision = "20261003_0017"
branch_labels = None
depends_on = None

_COLUMNS = ("sol_tier_small", "sol_tier_medium", "sol_tier_large")


def upgrade():
    with op.batch_alter_table("trading_control") as batch:
        for name in _COLUMNS:
            batch.add_column(sa.Column(name, sa.Numeric(18, 9), nullable=True))


def downgrade():
    with op.batch_alter_table("trading_control") as batch:
        for name in reversed(_COLUMNS):
            batch.drop_column(name)
