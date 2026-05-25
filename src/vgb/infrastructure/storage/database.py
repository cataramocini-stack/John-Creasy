"""Gerenciamento do banco de dados async."""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vgb.infrastructure.storage.models import Base


class Database:
    """Wrapper para engine e sessoes do SQLAlchemy async."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url, echo=False, future=True)
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        await self.engine.dispose()
