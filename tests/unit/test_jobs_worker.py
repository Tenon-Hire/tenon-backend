from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.jobs import worker
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from tests.factories import create_company


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
async def test_compute_backoff_seconds():
    assert worker.compute_backoff_seconds(0) == 1
    assert worker.compute_backoff_seconds(1) == 1
    assert worker.compute_backoff_seconds(2) == 2
    assert worker.compute_backoff_seconds(3) == 4
    assert worker.compute_backoff_seconds(20) == 60


@pytest.mark.asyncio
async def test_run_once_returns_false_when_no_jobs(async_session):
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-empty",
        now=datetime.now(UTC),
    )
    assert handled is False


@pytest.mark.asyncio
async def test_run_once_succeeds_and_marks_result(async_session):
    company = await create_company(async_session, name="Worker Success Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_success",
        idempotency_key="worker-success-1",
        payload_json={"x": 1},
        company_id=company.id,
    )

    async def _handler(payload):
        assert payload == {"x": 1}
        return {"ok": True}

    worker.register_handler("worker_success", _handler)
    now = datetime.now(UTC)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-success",
        now=now,
    )
    assert handled is True
    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_SUCCEEDED
    assert refreshed.attempt == 1
    assert refreshed.result_json == {"ok": True}
    assert refreshed.last_error is None


@pytest.mark.asyncio
async def test_run_once_retries_then_dead_letters(async_session):
    company = await create_company(async_session, name="Worker Retry Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_retry",
        idempotency_key="worker-retry-1",
        payload_json={"x": 2},
        company_id=company.id,
        max_attempts=2,
    )

    async def _handler(_payload):
        raise RuntimeError("temporary failure")

    worker.register_handler("worker_retry", _handler)
    first_now = datetime.now(UTC)
    first = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-retry",
        now=first_now,
    )
    assert first is True

    first_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_QUEUED
    assert first_refresh.attempt == 1
    assert first_refresh.next_run_at is not None
    observed_next_run = first_refresh.next_run_at
    if observed_next_run.tzinfo is None:
        observed_next_run = observed_next_run.replace(tzinfo=UTC)
    assert observed_next_run == first_now + timedelta(seconds=1)
    assert "RuntimeError" in (first_refresh.last_error or "")

    second_now = first_now + timedelta(seconds=1)
    second = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-retry",
        now=second_now,
    )
    assert second is True

    second_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_DEAD_LETTER
    assert second_refresh.attempt == 2
    assert second_refresh.next_run_at is None


@pytest.mark.asyncio
async def test_run_once_dead_letters_when_handler_missing(async_session):
    company = await create_company(async_session, name="Worker Missing Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_missing_handler",
        idempotency_key="worker-missing-1",
        payload_json={"x": 3},
        company_id=company.id,
    )
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-missing",
        now=datetime.now(UTC),
    )
    assert handled is True
    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_DEAD_LETTER
    assert "no handler registered" in (refreshed.last_error or "")


@pytest.mark.asyncio
async def test_run_once_keeps_handler_rescheduled_job_queued(async_session):
    company = await create_company(async_session, name="Worker Rescheduled Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_handler_rescheduled",
        idempotency_key="worker-rescheduled-1",
        payload_json={"x": 4},
        company_id=company.id,
    )
    now = datetime.now(UTC)
    next_run_at = now + timedelta(hours=1)

    async def _handler(_payload):
        await jobs_repo.requeue_nonterminal_idempotent_job(
            async_session,
            company_id=company.id,
            job_type=job.job_type,
            idempotency_key=job.idempotency_key,
            next_run_at=next_run_at,
            now=now,
            payload_json={"x": 4},
            commit=True,
        )
        return {"_jobDisposition": "rescheduled"}

    worker.register_handler("worker_handler_rescheduled", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-handler-rescheduled",
        now=now,
    )
    assert handled is True

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    observed_next_run = refreshed.next_run_at
    assert observed_next_run is not None
    if observed_next_run.tzinfo is None:
        observed_next_run = observed_next_run.replace(tzinfo=UTC)
    assert observed_next_run == next_run_at
    assert refreshed.result_json is None


@pytest.mark.asyncio
async def test_run_once_reschedule_disposition_without_requeue_is_retried(
    async_session,
):
    company = await create_company(async_session, name="Worker Bad Reschedule Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_handler_bad_rescheduled",
        idempotency_key="worker-bad-rescheduled-1",
        payload_json={"x": 5},
        company_id=company.id,
    )
    now = datetime.now(UTC)

    async def _handler(_payload):
        return {"_jobDisposition": "rescheduled"}

    worker.register_handler("worker_handler_bad_rescheduled", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-handler-bad-rescheduled",
        now=now,
    )
    assert handled is True

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert "handler_reschedule_failed" in (refreshed.last_error or "")
    assert refreshed.result_json is None


@pytest.mark.asyncio
async def test_run_once_reschedule_disposition_without_requeue_dead_letters_at_max(
    async_session,
):
    company = await create_company(async_session, name="Worker Bad Reschedule Max Co")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="worker_handler_bad_rescheduled_max",
        idempotency_key="worker-bad-rescheduled-max-1",
        payload_json={"x": 6},
        company_id=company.id,
        max_attempts=1,
    )
    now = datetime.now(UTC)

    async def _handler(_payload):
        return {"_jobDisposition": "rescheduled"}

    worker.register_handler("worker_handler_bad_rescheduled_max", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-handler-bad-rescheduled-max",
        now=now,
    )
    assert handled is True

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_DEAD_LETTER
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert "handler_reschedule_failed" in (refreshed.last_error or "")
