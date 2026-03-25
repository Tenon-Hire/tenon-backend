from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.shared.database.shared_database_models_model import Base

settings.ENV = "test"
settings.RATE_LIMIT_ENABLED = None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    test_url = os.getenv("TEST_DATABASE_URL") or "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_url, echo=False, pool_pre_ping=True, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(name="async_session")
async def _async_session_alias(db_session: AsyncSession) -> AsyncSession:
    return db_session
