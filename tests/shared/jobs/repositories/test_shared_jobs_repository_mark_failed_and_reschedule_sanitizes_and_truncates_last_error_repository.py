from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_mark_failed_and_reschedule_sanitizes_and_truncates_last_error(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Error Hygiene")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-error-hygiene",
        payload_json={"ok": True},
        company_id=company.id,
    )

    now = datetime.now(UTC)
    raw_error = "RuntimeError:\n" + ("temporary\tfailure\n" * 600)
    await jobs_repo.mark_failed_and_reschedule(
        async_session,
        job_id=job.id,
        error_str=raw_error,
        next_run_at=now + timedelta(seconds=5),
        now=now,
    )

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.last_error is not None
    assert len(refreshed.last_error) <= jobs_repo.MAX_JOB_ERROR_CHARS
    assert "\n" not in refreshed.last_error
    assert "\r" not in refreshed.last_error
