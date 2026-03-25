from __future__ import annotations

import pytest

from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_skips_non_text_and_missing_window(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="day-close-skip@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    tasks[4].type = "code"  # Day 5 should be ignored by text-task filter.
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    def _fake_compute_task_window(_candidate_session, task):
        if task.day_index == 1:
            return SimpleNamespace(window_end_at=None)
        return SimpleNamespace(window_end_at=datetime.now(UTC) + timedelta(hours=1))

    monkeypatch.setattr(
        day_close_jobs, "compute_task_window", _fake_compute_task_window
    )

    jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert jobs == []
