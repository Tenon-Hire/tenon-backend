# tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Build async DB URL from the sync one dynamically.
ASYNC_DB_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """
    Simple per-test async session.

    - Creates an async engine to the test DB
    - Yields a single AsyncSession
    - Disposes the engine after the test

    Schema is assumed to already exist (via Alembic migrations).
    """
    engine = create_async_engine(ASYNC_DB_URL, echo=False, future=True)
    SessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with SessionLocal() as session:
        yield session

    await engine.dispose()
