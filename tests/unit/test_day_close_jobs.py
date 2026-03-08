from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.candidate_sessions import day_close_jobs
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def test_day_close_job_helpers_format_payload() -> None:
    key = day_close_jobs.day_close_finalize_text_idempotency_key(11, 22)
    assert key == "day_close_finalize_text:11:22"
    enforcement_key = day_close_jobs.day_close_enforcement_idempotency_key(11, 2)
    assert enforcement_key == "day_close_enforcement:11:2"

    window_end = datetime(2026, 3, 10, 18, 30, tzinfo=UTC)
    payload = day_close_jobs.build_day_close_finalize_text_payload(
        candidate_session_id=11,
        task_id=22,
        day_index=5,
        window_end_at=window_end,
    )
    assert payload == {
        "candidateSessionId": 11,
        "taskId": 22,
        "dayIndex": 5,
        "windowEndAt": "2026-03-10T18:30:00Z",
    }
    enforcement_payload = day_close_jobs.build_day_close_enforcement_payload(
        candidate_session_id=11,
        task_id=33,
        day_index=2,
        window_end_at=window_end,
    )
    assert enforcement_payload == {
        "candidateSessionId": 11,
        "taskId": 33,
        "dayIndex": 2,
        "windowEndAt": "2026-03-10T18:30:00Z",
    }


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_returns_empty_without_simulation(async_session):
    candidate_session = SimpleNamespace(simulation=None)
    jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
    )
    assert jobs == []


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_returns_empty_without_simulation(
    async_session,
):
    candidate_session = SimpleNamespace(simulation=None)
    jobs = await day_close_jobs.enqueue_day_close_enforcement_jobs(
        async_session,
        candidate_session=candidate_session,
    )
    assert jobs == []


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_creates_day1_and_day5_jobs(async_session):
    recruiter = await create_recruiter(async_session, email="day-close-jobs@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
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


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_updates_existing_job_schedule(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="day-close-reschedule@test.com"
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    base = datetime(2026, 3, 10, 18, 30, tzinfo=UTC)
    window_end_a = {1: base, 5: base + timedelta(days=4)}
    window_end_b = {
        1: base + timedelta(hours=2),
        5: base + timedelta(days=4, hours=3),
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

    first_jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert len(first_jobs) == 2
    first_job_ids = {job.id for job in first_jobs}

    phase["value"] = "b"
    second_jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
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


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_creates_day2_and_day3_jobs(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="day-close-enforce@test.com"
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    jobs = await day_close_jobs.enqueue_day_close_enforcement_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )

    assert len(jobs) == 2
    assert {job.payload_json["dayIndex"] for job in jobs} == {2, 3}
    assert all(job.next_run_at is not None for job in jobs)


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_updates_existing_job_schedule(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="day-close-enforce-reschedule@test.com"
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
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


@pytest.mark.asyncio
async def test_enqueue_day_close_enforcement_jobs_skips_non_code_and_missing_window(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="day-close-enforce-skip@test.com"
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    tasks[2].type = "documentation"  # Day 3 should be ignored by code-task filter.
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    def _fake_compute_task_window(_candidate_session, task):
        if task.day_index == 2:
            return SimpleNamespace(window_end_at=None)
        return SimpleNamespace(window_end_at=datetime.now(UTC) + timedelta(hours=1))

    monkeypatch.setattr(
        day_close_jobs,
        "compute_task_window",
        _fake_compute_task_window,
    )

    jobs = await day_close_jobs.enqueue_day_close_enforcement_jobs(
        async_session,
        candidate_session=candidate_session,
        commit=True,
    )
    assert jobs == []
