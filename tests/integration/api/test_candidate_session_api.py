from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.routers import candidate_sessions as candidate_routes
from app.core.auth.principal import Principal, get_principal
from app.core.settings import settings
from app.domains import Task
from app.domains.candidate_sessions import repository as cs_repo
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
)
from app.repositories.recordings import repository as recordings_repo
from app.services.scheduling.day_windows import serialize_day_windows
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


def _principal(
    email: str, *, sub: str | None = None, email_verified: bool | None = True
) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    claims = {
        "sub": sub or f"candidate-{email}",
        "email": email,
        email_claim: email,
        "permissions": ["candidate:access"],
        permissions_claim: ["candidate:access"],
    }
    if email_verified is not None:
        claims["email_verified"] = email_verified
    return Principal(
        sub=sub or f"candidate-{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=["candidate:access"],
        claims=claims,
    )


def _task_for_day(tasks: list[Task], *, day_index: int) -> Task:
    return next(task for task in tasks if task.day_index == day_index)


def _set_day4_day5_transition_windows(candidate_session, *, day5_open: bool) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    always_open_start = now - timedelta(days=1)
    always_open_end = now + timedelta(days=1)

    if day5_open:
        day4_start = now - timedelta(hours=6)
        day4_end = now - timedelta(hours=4)
        day5_start = now - timedelta(hours=1)
        day5_end = now + timedelta(hours=1)
    else:
        day4_start = now - timedelta(hours=1)
        day4_end = now + timedelta(hours=1)
        day5_start = now + timedelta(hours=3)
        day5_end = now + timedelta(hours=5)

    candidate_session.scheduled_start_at = always_open_start
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(
        [
            {
                "dayIndex": 1,
                "windowStartAt": always_open_start,
                "windowEndAt": always_open_end,
            },
            {
                "dayIndex": 2,
                "windowStartAt": always_open_start,
                "windowEndAt": always_open_end,
            },
            {
                "dayIndex": 3,
                "windowStartAt": always_open_start,
                "windowEndAt": always_open_end,
            },
            {
                "dayIndex": 4,
                "windowStartAt": day4_start,
                "windowEndAt": day4_end,
            },
            {
                "dayIndex": 5,
                "windowStartAt": day5_start,
                "windowEndAt": day5_end,
            },
        ]
    )


async def _complete_handoff_upload(
    *,
    async_client,
    async_session,
    candidate_session,
    task_id: int,
    filename: str,
    size_bytes: int,
) -> str:
    headers = {
        "Authorization": f"Bearer candidate:{candidate_session.invite_email}",
        "x-candidate-session-id": str(candidate_session.id),
    }
    init_response = await async_client.post(
        f"/api/tasks/{task_id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": size_bytes,
            "filename": filename,
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]

    recording = await recordings_repo.get_latest_for_task_session(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task_id,
    )
    assert recording is not None
    storage_provider = get_storage_media_provider()
    assert isinstance(storage_provider, FakeStorageMediaProvider)
    storage_provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task_id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text
    return recording_id


@pytest.mark.asyncio
async def test_resolve_session_transitions_to_in_progress(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="resolve@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    assert cs.status == "not_started"
    assert cs.started_at is None

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["status"] == "in_progress"
    assert body["candidateSessionId"] == cs.id
    assert body["claimedAt"] is not None

    await async_session.refresh(cs)
    assert cs.status == "in_progress"
    assert cs.started_at is not None
    assert cs.candidate_auth0_sub == f"candidate-{cs.invite_email}"


@pytest.mark.asyncio
async def test_current_task_marks_complete_when_all_tasks_done(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="progress@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        with_default_schedule=True,
    )

    # Seed submissions for all tasks to mimic completion.
    for task in tasks:
        await create_submission(
            async_session,
            candidate_session=cs,
            task=task,
            content_text=f"Answer for day {task.day_index}",
        )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["isComplete"] is True
    assert body["currentDayIndex"] is None
    assert body["currentTask"] is None
    assert body["progress"]["completed"] == len(tasks)

    await async_session.refresh(cs)
    assert cs.status == "completed"
    assert cs.completed_at is not None


@pytest.mark.asyncio
async def test_current_task_includes_cutoff_fields_when_day_audit_exists(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="current-cutoff@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    day2_task = next(task for task in tasks if task.day_index == 2)
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    cutoff_at = datetime(2026, 3, 8, 17, 45, tzinfo=UTC)
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=day2_task.day_index,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="abc123def456",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["currentTask"]["dayIndex"] == 2
    assert body["currentTask"]["cutoffCommitSha"] == "abc123def456"
    assert body["currentTask"]["cutoffAt"] == "2026-03-08T17:45:00Z"


@pytest.mark.asyncio
async def test_current_task_returns_null_cutoff_fields_when_day_audit_missing(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="current-cutoff-missing@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["currentTask"]["dayIndex"] == 2
    assert body["currentTask"]["cutoffCommitSha"] is None
    assert body["currentTask"]["cutoffAt"] is None


@pytest.mark.asyncio
async def test_current_task_keeps_day4_handoff_until_day5_window_opens(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="current-day4-handoff-window@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    day1_task = _task_for_day(tasks, day_index=1)
    day2_task = _task_for_day(tasks, day_index=2)
    day3_task = _task_for_day(tasks, day_index=3)
    day4_task = _task_for_day(tasks, day_index=4)
    day5_task = _task_for_day(tasks, day_index=5)

    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=False,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    _set_day4_day5_transition_windows(cs, day5_open=False)
    await create_submission(async_session, candidate_session=cs, task=day1_task)
    await create_submission(async_session, candidate_session=cs, task=day2_task)
    await create_submission(async_session, candidate_session=cs, task=day3_task)
    await async_session.commit()

    await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-first.mp4",
        size_bytes=2_048,
    )

    headers = {
        "Authorization": f"Bearer candidate:{cs.invite_email}",
        "x-candidate-session-id": str(cs.id),
    }
    first_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert first_view.status_code == 200, first_view.text
    first_body = first_view.json()
    assert first_body["currentTask"]["id"] == day4_task.id
    assert first_body["currentTask"]["dayIndex"] == 4
    assert first_body["currentTask"]["type"] == "handoff"

    revisit_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert revisit_view.status_code == 200, revisit_view.text
    revisit_body = revisit_view.json()
    assert revisit_body["currentTask"]["id"] == day4_task.id
    assert revisit_body["currentTask"]["dayIndex"] == 4

    _set_day4_day5_transition_windows(cs, day5_open=True)
    await async_session.commit()

    after_day5_open = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert after_day5_open.status_code == 200, after_day5_open.text
    after_day5_open_body = after_day5_open.json()
    assert after_day5_open_body["currentTask"]["id"] == day5_task.id
    assert after_day5_open_body["currentTask"]["dayIndex"] == 5


@pytest.mark.asyncio
async def test_handoff_resubmission_allowed_while_day4_is_current_before_day5_open(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="current-day4-resubmit-before-day5@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    day1_task = _task_for_day(tasks, day_index=1)
    day2_task = _task_for_day(tasks, day_index=2)
    day3_task = _task_for_day(tasks, day_index=3)
    day4_task = _task_for_day(tasks, day_index=4)

    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=False,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    _set_day4_day5_transition_windows(cs, day5_open=False)
    await create_submission(async_session, candidate_session=cs, task=day1_task)
    await create_submission(async_session, candidate_session=cs, task=day2_task)
    await create_submission(async_session, candidate_session=cs, task=day3_task)
    await async_session.commit()

    first_recording_id = await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-first-resubmit.mp4",
        size_bytes=2_048,
    )
    second_recording_id = await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-second-resubmit.mp4",
        size_bytes=2_049,
    )
    assert second_recording_id != first_recording_id

    headers = {
        "Authorization": f"Bearer candidate:{cs.invite_email}",
        "x-candidate-session-id": str(cs.id),
    }
    current_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert current_view.status_code == 200, current_view.text
    current_body = current_view.json()
    assert current_body["currentTask"]["id"] == day4_task.id
    assert current_body["currentTask"]["dayIndex"] == 4


@pytest.mark.asyncio
async def test_invites_list_shows_candidates_for_email(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="list@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs_match = await create_candidate_session(async_session, simulation=sim)
    await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="other@example.com",
        candidate_name="Other",
    )

    res = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": f"Bearer candidate:{cs_match.invite_email}"},
    )
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) == 1
    assert items[0]["candidateSessionId"] == cs_match.id


@pytest.mark.asyncio
async def test_claim_endpoint_forbidden_on_mismatch(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="claimfail@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="other@example.com",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": "Bearer candidate:other@example.com"},
    )
    assert res.status_code == 403
    body = res.json()
    assert body["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
    assert body["retryable"] is False
    assert body["details"] == {}


@pytest.mark.asyncio
async def test_claim_endpoint_rejects_unverified_email(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="verifyfalse@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    async def _override_get_principal():
        return _principal(cs.invite_email, email_verified=False)

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.post(
            f"/api/candidate/session/{cs.token}/claim",
            headers={"Authorization": "Bearer ignored"},
        )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_claim_endpoint_rejects_missing_email_verified_claim(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="verifymissing@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    async def _override_get_principal():
        return _principal(cs.invite_email, email_verified=None)

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.post(
            f"/api/candidate/session/{cs.token}/claim",
            headers={"Authorization": "Bearer ignored"},
        )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_get_current_task_respects_expiry(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="expired@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        expires_in_days=-1,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(days=2),
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_resolve_invalid_token(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="invalid@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    res = await async_client.get(
        "/api/candidate/session/" + "x" * 24,
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_resolve_expired_token_returns_410(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="expired-resolve@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        expires_in_days=-1,
        status="not_started",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_candidate_claim_rate_limited_in_prod(
    async_client, async_session, monkeypatch
):
    monkeypatch.setattr(settings, "ENV", "prod")
    candidate_routes.rate_limit.limiter.reset()
    original_rule = candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT
    candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT = (
        candidate_routes.rate_limit.RateLimitRule(limit=1, window_seconds=60.0)
    )

    recruiter = await create_recruiter(async_session, email="claim-rate@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    first = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert first.status_code == 200, first.text

    second = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert second.status_code == 429

    candidate_routes.CANDIDATE_CLAIM_RATE_LIMIT = original_rule
    candidate_routes.rate_limit.limiter.reset()


@pytest.mark.asyncio
async def test_current_task_token_mismatch(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="tm@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    claim = await async_client.post(
        f"/api/candidate/session/{cs.token}/claim",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert claim.status_code == 200, claim.text

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:other@example.com",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"


@pytest.mark.asyncio
async def test_current_task_revalidates_claimed_sub_each_request(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="claimed-sub@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    claim = await async_client.post(
        f"/api/candidate/session/{cs.token}/claim",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert claim.status_code == 200, claim.text

    async def _override_get_principal():
        return _principal(
            cs.invite_email,
            sub=f"candidate-alt-{cs.invite_email}",
            email_verified=True,
        )

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.get(
            f"/api/candidate/session/{cs.id}/current_task",
            headers={"x-candidate-session-id": str(cs.id)},
        )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_SESSION_ALREADY_CLAIMED"


@pytest.mark.asyncio
async def test_current_task_unclaimed_session_requires_verified_email_and_invite_match(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="unclaimed-id@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner@example.com",
        with_default_schedule=True,
    )
    route = f"/api/candidate/session/{cs.id}/current_task"
    headers = {"x-candidate-session-id": str(cs.id)}

    async def _principal_wrong_email():
        return _principal(
            "attacker@example.com",
            sub="candidate-attacker@example.com",
            email_verified=True,
        )

    with override_dependencies({get_principal: _principal_wrong_email}):
        mismatch = await async_client.get(route, headers=headers)
    assert mismatch.status_code == 403
    assert mismatch.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"

    async def _principal_unverified():
        return _principal(
            cs.invite_email,
            sub=f"candidate-{cs.invite_email}",
            email_verified=False,
        )

    with override_dependencies({get_principal: _principal_unverified}):
        unverified = await async_client.get(route, headers=headers)
    assert unverified.status_code == 403
    assert unverified.json()["errorCode"] == "CANDIDATE_EMAIL_NOT_VERIFIED"

    async def _principal_missing_verified():
        return _principal(
            cs.invite_email,
            sub=f"candidate-{cs.invite_email}",
            email_verified=None,
        )

    with override_dependencies({get_principal: _principal_missing_verified}):
        missing_verified = await async_client.get(route, headers=headers)
    assert missing_verified.status_code == 403
    assert missing_verified.json()["errorCode"] == "CANDIDATE_EMAIL_NOT_VERIFIED"

    expected_sub = "candidate-owner@example.com"

    async def _principal_owner_verified():
        return _principal(
            "  OWNER@EXAMPLE.COM  ",
            sub=expected_sub,
            email_verified=True,
        )

    with override_dependencies({get_principal: _principal_owner_verified}):
        ok = await async_client.get(route, headers=headers)
    assert ok.status_code == 200, ok.text

    await async_session.refresh(cs)
    assert cs.candidate_auth0_sub == expected_sub
    assert cs.claimed_at is not None


@pytest.mark.asyncio
async def test_current_task_no_tasks_returns_500(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="notasks@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Remove all tasks to trigger guard
    await async_session.execute(select(Task))  # ensure tasks loaded
    for t in tasks:
        await async_session.delete(t)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 500
