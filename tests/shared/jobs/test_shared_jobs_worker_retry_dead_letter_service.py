from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.shared.jobs import worker
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
)
from tests.shared.jobs.shared_jobs_worker_utils import _session_maker, create_job


@pytest.mark.asyncio
async def test_run_once_retries_then_dead_letters(async_session):
    job = await create_job(
        async_session,
        job_type="worker_retry",
        idempotency_key="worker-retry-1",
        payload_json={"x": 2},
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

    second = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-retry",
        now=first_now + timedelta(seconds=1),
    )
    assert second is True

    second_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_DEAD_LETTER
    assert second_refresh.attempt == 2
    assert second_refresh.next_run_at is None


@pytest.mark.asyncio
async def test_run_once_dead_letters_when_handler_missing(async_session):
    job = await create_job(
        async_session,
        job_type="worker_missing_handler",
        idempotency_key="worker-missing-1",
        payload_json={"x": 3},
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
