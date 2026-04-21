from __future__ import annotations

import pytest

from app.candidates.candidate_sessions.services import schedule_gates
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_day_windows,
    serialize_day_windows,
)
from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


@pytest.mark.asyncio
async def test_day5_extended_window_stays_open_until_nine_pm_local(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="day5-window@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=False,
    )

    candidate_timezone = "America/New_York"
    scheduled_start_at = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=candidate_timezone,
        day_window_start_local=trial.day_window_start_local,
        day_window_end_local=trial.day_window_end_local,
        overrides=trial.day_window_overrides_json,
        overrides_enabled=bool(trial.day_window_overrides_enabled),
        total_days=5,
    )

    candidate_session.scheduled_start_at = scheduled_start_at
    candidate_session.candidate_timezone = candidate_timezone
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()

    day1_window = day_windows[0]
    day5_window = day_windows[4]
    assert day1_window["windowEndAt"] == datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    assert day5_window["windowEndAt"] == datetime(2026, 3, 15, 1, 0, tzinfo=UTC)

    day5_task = tasks[4]
    open_window = schedule_gates.compute_task_window(
        candidate_session,
        day5_task,
        now_utc=datetime(2026, 3, 14, 22, 30, tzinfo=UTC),
    )
    assert open_window.is_open is True
    assert open_window.window_end_at == day5_window["windowEndAt"]
    assert open_window.next_open_at is None

    closed_window = schedule_gates.compute_task_window(
        candidate_session,
        day5_task,
        now_utc=datetime(2026, 3, 15, 1, 1, tzinfo=UTC),
    )
    assert closed_window.is_open is False
    assert closed_window.window_end_at == day5_window["windowEndAt"]
    assert closed_window.next_open_at is None

    jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert len(jobs) == 2
    day5_job = next(job for job in jobs if job.payload_json["dayIndex"] == 5)
    assert day5_job.payload_json["windowEndAt"] == "2026-03-15T01:00:00Z"
    next_run_at = day5_job.next_run_at
    assert next_run_at is not None
    if next_run_at.tzinfo is None:
        next_run_at = next_run_at.replace(tzinfo=UTC)
    assert next_run_at == day5_window["windowEndAt"]
