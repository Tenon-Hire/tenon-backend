from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs import worker
from app.shared.jobs.repositories import repository as jobs_repo
from tests.shared.factories import create_company


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def create_job(
    async_session: AsyncSession,
    *,
    job_type: str,
    idempotency_key: str,
    payload_json: dict[str, object],
    max_attempts: int | None = None,
):
    company = await create_company(async_session, name=f"{job_type}-company")
    kwargs = {
        "job_type": job_type,
        "idempotency_key": idempotency_key,
        "payload_json": payload_json,
        "company_id": company.id,
    }
    if max_attempts is not None:
        kwargs["max_attempts"] = max_attempts
    return await jobs_repo.create_or_get_idempotent(
        async_session,
        **kwargs,
    )
