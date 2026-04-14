from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
)
from tests.shared.jobs.shared_jobs_worker_utils import create_job


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@pytest.mark.asyncio
async def test_requeue_dead_letter_jobs_only_targets_dead_letters(async_session):
    dead_letter_job = await create_job(
        async_session,
        job_type="dead-letter-retry",
        idempotency_key="dead-letter-1",
        payload_json={"demo": True},
    )
    dead_letter_job.status = JOB_STATUS_DEAD_LETTER
    dead_letter_job.last_error = "schema repair required"
    dead_letter_job.result_json = {"failure": True}
    dead_letter_job.locked_at = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    dead_letter_job.locked_by = "worker-1"

    queued_job = await create_job(
        async_session,
        job_type="queued-preserved",
        idempotency_key="queued-1",
        payload_json={"demo": True},
    )
    queued_job.next_run_at = datetime.now(UTC) + timedelta(minutes=10)
    await async_session.commit()

    now = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    count = await jobs_repo.requeue_dead_letter_jobs(async_session, now=now)
    assert count == 1

    refreshed_dead = await jobs_repo.get_by_id(async_session, dead_letter_job.id)
    assert refreshed_dead is not None
    assert refreshed_dead.status == JOB_STATUS_QUEUED
    assert _to_utc(refreshed_dead.next_run_at) == now
    assert refreshed_dead.locked_at is None
    assert refreshed_dead.locked_by is None
    assert refreshed_dead.last_error is None
    assert refreshed_dead.result_json is None

    refreshed_queued = await jobs_repo.get_by_id(async_session, queued_job.id)
    assert refreshed_queued is not None
    assert refreshed_queued.status == JOB_STATUS_QUEUED
    assert refreshed_queued.next_run_at is not None


@pytest.mark.asyncio
async def test_requeue_dead_letter_jobs_can_target_specific_ids(async_session):
    first = await create_job(
        async_session,
        job_type="dead-letter-retry-target",
        idempotency_key="dead-letter-target-1",
        payload_json={"demo": True},
    )
    second = await create_job(
        async_session,
        job_type="dead-letter-retry-target-2",
        idempotency_key="dead-letter-target-2",
        payload_json={"demo": True},
    )
    first.status = JOB_STATUS_DEAD_LETTER
    second.status = JOB_STATUS_DEAD_LETTER
    await async_session.commit()

    count = await jobs_repo.requeue_dead_letter_jobs(
        async_session,
        now=datetime(2026, 4, 14, 13, 30, tzinfo=UTC),
        job_ids=[first.id],
    )
    assert count == 1

    refreshed_first = await jobs_repo.get_by_id(async_session, first.id)
    refreshed_second = await jobs_repo.get_by_id(async_session, second.id)
    assert refreshed_first is not None
    assert refreshed_first.status == JOB_STATUS_QUEUED
    assert refreshed_second is not None
    assert refreshed_second.status == JOB_STATUS_DEAD_LETTER


@pytest.mark.asyncio
async def test_requeue_dead_letter_jobs_ignores_blank_targets(async_session):
    count = await jobs_repo.requeue_dead_letter_jobs(
        async_session,
        now=datetime(2026, 4, 14, 13, 45, tzinfo=UTC),
        job_ids=[" ", "\t"],
    )
    assert count == 0


@pytest.mark.asyncio
async def test_requeue_dead_letter_jobs_deduplicates_requested_ids(async_session):
    job = await create_job(
        async_session,
        job_type="dead-letter-retry-dedup",
        idempotency_key="dead-letter-dedup-1",
        payload_json={"demo": True},
    )
    job.status = JOB_STATUS_DEAD_LETTER
    await async_session.commit()

    count = await jobs_repo.requeue_dead_letter_jobs(
        async_session,
        now=datetime(2026, 4, 14, 14, 0, tzinfo=UTC),
        job_ids=[job.id, job.id, f" {job.id} "],
    )

    assert count == 1


@pytest.mark.asyncio
async def test_requeue_dead_letter_jobs_returns_zero_when_no_dead_letters(
    async_session,
):
    count = await jobs_repo.requeue_dead_letter_jobs(
        async_session,
        now=datetime(2026, 4, 14, 14, 15, tzinfo=UTC),
    )

    assert count == 0
