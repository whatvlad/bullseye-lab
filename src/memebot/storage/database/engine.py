from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from memebot.storage.database.models import Base


def create_database_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )


class Database:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def healthcheck(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def create_schema_for_tests(self) -> None:
        """Create all tables only for disposable tests; use Alembic elsewhere."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
