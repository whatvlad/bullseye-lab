from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def upgrade_database(database_url: str, revision: str = "head") -> None:
    project_root = Path(__file__).resolve().parents[4]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, revision)
