from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.config import settings
from app.shared.database.shared_database_models_model import Base

settings.ENV = "test"
settings.RATE_LIMIT_ENABLED = None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def db_engine():
    test_url = os.getenv("TEST_DATABASE_URL") or "sqlite+aiosqlite:///:memory:"
    engine_kwargs = {
        "echo": False,
        "future": True,
    }
    if test_url.startswith("sqlite+aiosqlite:///:memory:"):
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["poolclass"] = NullPool
    engine = create_async_engine(test_url, **engine_kwargs)

    async def _create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    yield engine

    asyncio.run(engine.dispose())


@pytest.fixture
def db_session(db_engine):
    async def _reset_schema() -> None:
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset_schema())
    session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )
    session = session_maker()
    yield session

    async def _close_session() -> None:
        await session.rollback()
        await session.close()

    asyncio.run(_close_session())


@pytest.fixture(name="async_session")
def _async_session_alias(db_session: AsyncSession) -> AsyncSession:
    return db_session
