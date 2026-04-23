from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_success_persists_windows_and_jobs(
    async_session, monkeypatch
):
    (
        tasks,
        candidate_session,
        principal,
        email_service,
    ) = await _seed_claimed_schedule_context(async_session)
    sent_events = _capture_schedule_notifications(monkeypatch)
    now = datetime.now(UTC)
    start_at = now + timedelta(days=1)

    result = await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        github_username="octocat",
        email_service=email_service,
        now=now,
        correlation_id="req-1",
    )
    assert result.created is True
    assert result.candidate_session.schedule_locked_at is not None
    assert result.candidate_session.github_username == "octocat"
    assert result.candidate_session.day_windows_json is not None
    for window in result.candidate_session.day_windows_json:
        assert isinstance(window["dayIndex"], int)
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", window["windowStartAt"]
        )
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", window["windowEndAt"]
        )
    assert sent_events == [(candidate_session.id, "req-1")]

    finalize_jobs = await _list_jobs(
        async_session,
        candidate_session_id=candidate_session.id,
        job_type="day_close_finalize_text",
    )
    assert len(finalize_jobs) == 2
    expected_task_ids = {task.id for task in tasks if task.day_index in {1, 5}}
    assert {job.payload_json["taskId"] for job in finalize_jobs} == expected_task_ids
    assert {job.payload_json["dayIndex"] for job in finalize_jobs} == {1, 5}
    for job in finalize_jobs:
        assert job.next_run_at is not None
        assert job.idempotency_key.startswith("day_close_finalize_text:")
        assert isinstance(job.payload_json["windowEndAt"], str)

    enforcement_jobs = await _list_jobs(
        async_session,
        candidate_session_id=candidate_session.id,
        job_type="day_close_enforcement",
    )
    assert len(enforcement_jobs) == 2
    expected_enforcement_ids = {task.id for task in tasks if task.day_index in {2, 3}}
    assert {
        job.payload_json["taskId"] for job in enforcement_jobs
    } == expected_enforcement_ids
    assert {job.payload_json["dayIndex"] for job in enforcement_jobs} == {2, 3}
    for job in enforcement_jobs:
        assert job.next_run_at is not None
        assert job.idempotency_key.startswith("day_close_enforcement:")
        assert isinstance(job.payload_json["windowEndAt"], str)


@pytest.mark.asyncio
async def test_schedule_candidate_session_allows_unverified_email_on_claimed_session(
    async_session,
):
    (
        _tasks,
        candidate_session,
        _seeded_principal,
        email_service,
    ) = await _seed_claimed_schedule_context(async_session)
    unverified_principal = _principal(
        candidate_session.invite_email,
        sub=candidate_session.candidate_auth0_sub,
        email_verified=False,
    )
    now = datetime.now(UTC)

    result = await schedule_service.schedule_candidate_session(
        async_session,
        token=candidate_session.token,
        principal=unverified_principal,
        scheduled_start_at=now + timedelta(days=1),
        candidate_timezone="America/New_York",
        github_username="octocat",
        email_service=email_service,
        now=now,
    )
    assert result.created is True
    assert result.candidate_session.schedule_locked_at is not None
    assert (
        result.candidate_session.candidate_auth0_sub
        == candidate_session.candidate_auth0_sub
    )
