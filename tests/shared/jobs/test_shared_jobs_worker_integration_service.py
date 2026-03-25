from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs import worker
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.factories import create_company


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


@pytest.mark.asyncio
async def test_worker_run_once_retry_then_success_with_new_sessions(async_session):
    session_maker = _session_maker(async_session)
    company = await create_company(async_session, name="Worker Integration Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="integration_retry_once",
        idempotency_key="integration-retry-once",
        payload_json={"step": "start"},
        company_id=company.id,
        max_attempts=3,
    )

    calls = {"count": 0}

    async def _handler(_payload):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("first attempt fails")
        return {"done": True}

    worker.register_handler("integration_retry_once", _handler)
    first_now = datetime.now(UTC)
    first_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="worker-int-1",
        now=first_now,
    )
    assert first_handled is True

    async with session_maker() as check_session:
        after_first = await jobs_repo.get_by_id(check_session, job.id)
        assert after_first is not None
        assert after_first.status == JOB_STATUS_QUEUED
        assert after_first.attempt == 1
        assert after_first.next_run_at is not None
        observed_next_run = after_first.next_run_at
        if observed_next_run.tzinfo is None:
            observed_next_run = observed_next_run.replace(tzinfo=UTC)
        assert observed_next_run == first_now + timedelta(seconds=1)

    second_now = first_now + timedelta(seconds=1)
    second_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="worker-int-2",
        now=second_now,
    )
    assert second_handled is True

    async with session_maker() as check_session:
        after_second = await jobs_repo.get_by_id(check_session, job.id)
        assert after_second is not None
        assert after_second.status == JOB_STATUS_SUCCEEDED
        assert after_second.attempt == 2
        assert after_second.result_json == {"done": True}
