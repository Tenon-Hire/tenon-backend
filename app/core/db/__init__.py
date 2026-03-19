from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import settings


def _create_engine():
    return create_async_engine(
        settings.database.async_url,
        echo=False,
        pool_pre_ping=True,
        future=True,
    )


engine = _create_engine()

async_session_maker = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

AsyncSessionLocal = async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a scoped async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db_if_needed() -> None:
    """No-op: local/test environments must run Alembic against PostgreSQL."""
    return
