from __future__ import annotations

import pytest

from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_creates_day1_and_day5_jobs(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="day-close-jobs@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )

    assert len(jobs) == 2
    assert {job.payload_json["dayIndex"] for job in jobs} == {1, 5}
    assert all(job.next_run_at is not None for job in jobs)
