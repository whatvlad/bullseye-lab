"""Widen optional wallet return percentages without clipping historical evidence."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0017"
down_revision = "20261001_0016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wallet_token_outcomes") as batch:
        for name in ("realized_return_percent", "mfe_percent", "mae_percent"):
            batch.alter_column(name, existing_type=sa.Numeric(18, 8), type_=sa.Numeric(50, 8))


def downgrade():
    # PostgreSQL refuses narrowing if values do not fit; never silently clip them.
    with op.batch_alter_table("wallet_token_outcomes") as batch:
        for name in ("realized_return_percent", "mfe_percent", "mae_percent"):
            batch.alter_column(name, existing_type=sa.Numeric(50, 8), type_=sa.Numeric(18, 8))
