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
async def test_run_once_keeps_handler_rescheduled_job_queued(async_session):
    job = await create_job(
        async_session,
        job_type="worker_handler_rescheduled",
        idempotency_key="worker-rescheduled-1",
        payload_json={"x": 4},
    )
    now = datetime.now(UTC)
    next_run_at = now + timedelta(hours=1)

    async def _handler(payload):
        await jobs_repo.requeue_nonterminal_idempotent_job(
            async_session,
            company_id=job.company_id,
            job_type=job.job_type,
            idempotency_key=job.idempotency_key,
            next_run_at=next_run_at,
            now=now,
            payload_json=payload,
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
    job = await create_job(
        async_session,
        job_type="worker_handler_bad_rescheduled",
        idempotency_key="worker-bad-rescheduled-1",
        payload_json={"x": 5},
    )

    async def _handler(_payload):
        return {"_jobDisposition": "rescheduled"}

    worker.register_handler("worker_handler_bad_rescheduled", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-handler-bad-rescheduled",
        now=datetime.now(UTC),
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
    job = await create_job(
        async_session,
        job_type="worker_handler_bad_rescheduled_max",
        idempotency_key="worker-bad-rescheduled-max-1",
        payload_json={"x": 6},
        max_attempts=1,
    )

    async def _handler(_payload):
        return {"_jobDisposition": "rescheduled"}

    worker.register_handler("worker_handler_bad_rescheduled_max", _handler)
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-handler-bad-rescheduled-max",
        now=datetime.now(UTC),
    )
    assert handled is True

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_DEAD_LETTER
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert "handler_reschedule_failed" in (refreshed.last_error or "")
