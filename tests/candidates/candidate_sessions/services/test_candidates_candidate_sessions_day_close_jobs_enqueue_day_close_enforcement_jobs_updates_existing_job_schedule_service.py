from __future__ import annotations

import pytest

from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_updates_existing_job_schedule(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="day-close-enforce-reschedule@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    base = datetime(2026, 3, 10, 18, 30, tzinfo=UTC)
    window_end_a = {2: base + timedelta(days=1), 3: base + timedelta(days=2)}
    window_end_b = {
        2: base + timedelta(days=1, hours=1),
        3: base + timedelta(days=2, hours=1),
    }
    phase = {"value": "a"}

    def _fake_compute_task_window(_candidate_session, task):
        selected = window_end_a if phase["value"] == "a" else window_end_b
        return SimpleNamespace(window_end_at=selected[task.day_index])

    monkeypatch.setattr(
        day_close_jobs,
        "compute_task_window",
        _fake_compute_task_window,
    )

    first_jobs = await day_close_jobs.enqueue_day_close_enforcement_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert len(first_jobs) == 2
    first_job_ids = {job.id for job in first_jobs}

    phase["value"] = "b"
    second_jobs = await day_close_jobs.enqueue_day_close_enforcement_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert len(second_jobs) == 2
    assert {job.id for job in second_jobs} == first_job_ids

    for job in second_jobs:
        day_index = int(job.payload_json["dayIndex"])
        next_run_at = job.next_run_at
        assert next_run_at is not None
        if next_run_at.tzinfo is None:
            next_run_at = next_run_at.replace(tzinfo=UTC)
        assert next_run_at == window_end_b[day_index]
        assert job.payload_json["windowEndAt"] == window_end_b[
            day_index
        ].isoformat().replace("+00:00", "Z")
