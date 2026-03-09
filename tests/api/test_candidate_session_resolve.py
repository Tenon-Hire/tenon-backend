from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domains import CandidateSession, Company, Simulation, Submission, Task, User
from app.jobs import worker
from app.services.scheduling.day_windows import (
    derive_day_windows,
    serialize_day_windows,
)

# -------------------------
# Shared helpers (mirrors resolve tests)
# -------------------------


async def _seed_recruiter(async_session, email: str = "recruiter1@tenon.com") -> User:
    company = Company(name="TestCo")
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    user = User(
        name="Recruiter One",
        email=email,
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


async def _create_simulation(async_client, async_session, recruiter_email: str) -> int:
    payload = {
        "title": "Backend Node Simulation",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Build new API feature and debug an issue",
    }
    res = await async_client.post(
        "/api/simulations",
        json=payload,
        headers={"x-dev-user-email": recruiter_email},
    )
    assert res.status_code in (200, 201), res.text
    sim_id = res.json()["id"]
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="candidate-session-resolve-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        json={"confirm": True},
        headers={"x-dev-user-email": recruiter_email},
    )
    assert activate.status_code == 200, activate.text
    return sim_id


async def _invite_candidate(
    async_client,
    sim_id: int,
    recruiter_email: str,
    invite_email: str = "jane@example.com",
) -> dict:
    payload = {"candidateName": "Jane Doe", "inviteEmail": invite_email}
    res = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        json=payload,
        headers={"x-dev-user-email": recruiter_email},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def _claim(async_client, token: str, email: str) -> dict:
    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": f"Bearer candidate:{email}"},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _next_local_window_start_utc(
    timezone_name: str, *, days_ahead: int = 1
) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC).replace(microsecond=0)


async def _apply_schedule(
    async_session,
    *,
    candidate_session_id: int,
    scheduled_start_at: datetime,
    candidate_timezone: str,
) -> None:
    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    sim = (
        await async_session.execute(
            select(Simulation).where(Simulation.id == cs.simulation_id)
        )
    ).scalar_one()
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=candidate_timezone,
        day_window_start_local=sim.day_window_start_local,
        day_window_end_local=sim.day_window_end_local,
        overrides=sim.day_window_overrides_json,
        overrides_enabled=bool(sim.day_window_overrides_enabled),
        total_days=5,
    )
    cs.scheduled_start_at = scheduled_start_at
    cs.candidate_timezone = candidate_timezone
    cs.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


# -------------------------
# Tests
# -------------------------


@pytest.mark.asyncio
async def test_current_task_initial_is_day_1(async_client, async_session, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=_next_local_window_start_utc(
            "America/New_York", days_ahead=-1
        ),
        candidate_timezone="America/New_York",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["candidateSessionId"] == cs_id
    assert body["isComplete"] is False
    assert body["currentDayIndex"] == 1
    assert body["currentTask"]["dayIndex"] == 1
    assert body["progress"]["completed"] == 0
    assert body["progress"]["total"] == 5
    assert body["currentTask"]["description"]
    assert body["currentWindow"] is not None
    assert body["currentWindow"]["windowStartAt"] is not None
    assert body["currentWindow"]["windowEndAt"] is not None
    assert isinstance(body["currentWindow"]["isOpen"], bool)
    assert body["currentWindow"]["now"] is not None


@pytest.mark.asyncio
async def test_current_task_pre_start_returns_schedule_not_started(
    async_client, async_session, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    recruiter_email = "recruiter-prestart@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)
    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]

    scheduled_start = _next_local_window_start_utc("America/New_York", days_ahead=2)
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=scheduled_start,
        candidate_timezone="America/New_York",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": "Bearer candidate:jane@example.com",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 409, res.text
    body = res.json()
    assert body["detail"] == "Simulation has not started yet."
    assert body["errorCode"] == "SCHEDULE_NOT_STARTED"
    assert body["retryable"] is True
    assert body["details"]["startAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowStartAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowEndAt"] is not None


@pytest.mark.asyncio
async def test_current_task_advances_after_submission(
    async_client, async_session, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=_next_local_window_start_utc(
            "America/New_York", days_ahead=-1
        ),
        candidate_timezone="America/New_York",
    )

    # Fetch Day 1 task
    day1_task = (
        await async_session.execute(
            select(Task).where(Task.simulation_id == sim_id, Task.day_index == 1)
        )
    ).scalar_one()

    # Insert submission for Day 1
    submission = Submission(
        candidate_session_id=cs_id,
        task_id=day1_task.id,
        submitted_at=datetime.now(UTC),
        content_text="My design solution",
    )
    async_session.add(submission)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["currentDayIndex"] == 2
    assert body["progress"]["completed"] == 1
    assert body["currentTask"]["dayIndex"] == 2


@pytest.mark.asyncio
async def test_current_task_completed_after_all_tasks(
    async_client, async_session, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=_next_local_window_start_utc(
            "America/New_York", days_ahead=-1
        ),
        candidate_timezone="America/New_York",
    )

    tasks = (
        (await async_session.execute(select(Task).where(Task.simulation_id == sim_id)))
        .scalars()
        .all()
    )

    now = datetime.now(UTC)

    for task in tasks:
        async_session.add(
            Submission(
                candidate_session_id=cs_id,
                task_id=task.id,
                submitted_at=now,
                content_text="done",
            )
        )

    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["isComplete"] is True
    assert body["currentTask"] is None
    assert body["currentDayIndex"] is None

    # DB state updated
    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()

    assert cs.status == "completed"
    assert cs.completed_at is not None


@pytest.mark.asyncio
async def test_current_task_expired_invite_410(async_client, async_session):
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"

    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()

    cs.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_resolve_transitions_to_in_progress(async_client, async_session):
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    token = invite["token"]
    cs_id = invite["candidateSessionId"]

    await _claim(async_client, token, "jane@example.com")
    access_token = "candidate:jane@example.com"

    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "in_progress"
    assert body["startedAt"] is not None
    assert body["candidateSessionId"] == cs_id

    cs_after = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()
    assert cs_after.status == "in_progress"
    assert cs_after.started_at is not None


@pytest.mark.asyncio
async def test_resolve_expired_token_returns_410(async_client, async_session):
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    token = invite["token"]
    cs_id = invite["candidateSessionId"]

    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()
    cs.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": "Bearer candidate:jane@example.com"},
    )
    assert res.status_code == 410
    assert res.json()["detail"] == "Invite token expired"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_resolve_invalid_token_returns_404(async_client, async_session):
    recruiter_email = "invalidtoken@test.com"
    await _seed_recruiter(async_session, recruiter_email)
    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)
    await _claim(async_client, invite["token"], "jane@example.com")
    access_token = "candidate:jane@example.com"

    res = await async_client.get(
        "/api/candidate/session/invalid-token-1234567890",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Invalid invite token"


@pytest.mark.asyncio
async def test_bootstrap_wrong_email_forbidden(async_client, async_session):
    recruiter_email = "wrongemail@test.com"
    await _seed_recruiter(async_session, recruiter_email)
    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)
    other_invite = await _invite_candidate(
        async_client,
        sim_id,
        recruiter_email,
        invite_email="other@example.com",
    )
    await _claim(async_client, other_invite["token"], "other@example.com")
    access_token = "candidate:other@example.com"

    res = await async_client.get(
        f"/api/candidate/session/{invite['token']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
