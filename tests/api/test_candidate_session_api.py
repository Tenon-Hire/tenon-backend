from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.routers import candidate_sessions as candidate_routes
from app.core.auth.principal import Principal, get_principal
from app.core.settings import settings
from app.domains import Task
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
