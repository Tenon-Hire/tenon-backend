from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domains import CandidateSession, Job, Simulation
from app.domains.common.types import CANDIDATE_SESSION_STATUS_COMPLETED
from app.domains.simulations import service as sim_service
from app.services.simulations import creation as sim_creation
from tests.factories import create_recruiter, create_simulation


@pytest.mark.asyncio
async def test_require_owned_simulation_raises(monkeypatch):
    async def _return_none(*_a, **_k):
        return None

    monkeypatch.setattr(sim_service.sim_repo, "get_owned", _return_none, raising=False)
    with pytest.raises(Exception) as excinfo:
        await sim_service.require_owned_simulation(db=None, simulation_id=1, user_id=2)
    assert excinfo.value.status_code == 404


def test_template_repo_for_task_variants(monkeypatch):
    monkeypatch.setattr(sim_service.settings.github, "GITHUB_TEMPLATE_OWNER", "owner")
    monkeypatch.setattr(
        sim_service, "resolve_template_repo_full_name", lambda _key: "template-only"
    )
    repo = sim_service._template_repo_for_task(5, "code", "python-fastapi")
    assert repo == "template-only"
    # Day index 2 uses owner override when repo name lacks owner prefix
    repo_with_owner = sim_service._template_repo_for_task(2, "code", "python-fastapi")
    assert repo_with_owner.startswith("owner/")
    assert sim_service._template_repo_for_task(1, "design", "python-fastapi") is None


def test_invite_url_uses_portal_base(monkeypatch):
    monkeypatch.setattr(
        sim_service.settings, "CANDIDATE_PORTAL_BASE_URL", "https://portal.test"
    )
    assert sim_service.invite_url("abc") == "https://portal.test/candidate/session/abc"


def test_create_simulation_payload_extractors_cover_context_branches():
    payload_with_dicts = SimpleNamespace(
        companyContext={"domain": "social"},
        ai={
            "noticeVersion": "mvp1",
            "noticeText": "Notice",
            "evalEnabledByDay": {"1": True},
        },
    )
    assert sim_creation._extract_company_context(payload_with_dicts) == {
        "domain": "social"
    }
    assert sim_creation._extract_ai_fields(payload_with_dicts) == (
        "mvp1",
        "Notice",
        {"1": True},
    )

    payload_with_object = SimpleNamespace(
        company_context={"productArea": "creator tools"},
        ai=SimpleNamespace(
            notice_version=None,
            noticeVersion="mvp2",
            notice_text=None,
            noticeText="Fallback",
            eval_enabled_by_day=None,
            evalEnabledByDay={"2": False},
        ),
    )
    assert sim_creation._extract_company_context(payload_with_object) == {
        "productArea": "creator tools"
    }
    assert sim_creation._extract_ai_fields(payload_with_object) == (
        "mvp2",
        "Fallback",
        {"2": False},
    )


def test_extract_day_window_config_normalizes_overrides():
    class _ModelOverride:
        def model_dump(self, by_alias=True):
            assert by_alias is True
            return {"startLocal": "10:00", "endLocal": "19:00"}

    payload_with_overrides = SimpleNamespace(
        dayWindowStartLocal=time(hour=8, minute=0),
        dayWindowEndLocal=time(hour=16, minute=0),
        dayWindowOverridesEnabled=True,
        dayWindowOverrides={
            9: _ModelOverride(),
            "10": {"startLocal": "11:00", "endLocal": "20:00"},
            "bad": object(),
        },
    )
    (
        start_local,
        end_local,
        enabled,
        overrides,
    ) = sim_creation._extract_day_window_config(payload_with_overrides)
    assert start_local == time(hour=8, minute=0)
    assert end_local == time(hour=16, minute=0)
    assert enabled is True
    assert overrides == {
        "9": {"startLocal": "10:00", "endLocal": "19:00"},
        "10": {"startLocal": "11:00", "endLocal": "20:00"},
    }

    payload_defaults = SimpleNamespace()
    (
        start_default,
        end_default,
        enabled_default,
        overrides_default,
    ) = sim_creation._extract_day_window_config(payload_defaults)
    assert start_default == time(hour=9, minute=0)
    assert end_default == time(hour=17, minute=0)
    assert enabled_default is False
    assert overrides_default is None


@pytest.mark.asyncio
async def test_create_invite_handles_token_collisions(monkeypatch):
    class StubSession:
        def __init__(self):
            self.flushes = 0
            self.added: CandidateSession | None = None

        def add(self, obj):
            self.added = obj

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            self.flushes += 1
            raise IntegrityError("", {}, None)

        async def execute(self, *_args, **_kwargs):
            class _Result:
                def scalar_one_or_none(self):
                    return None

            return _Result()

    with pytest.raises(Exception) as excinfo:
        await sim_service.create_invite(
            StubSession(),
            simulation_id=1,
            payload=type("P", (), {"candidateName": "x", "inviteEmail": "y"}),
        )
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_create_invite_integrity_error_returns_existing(monkeypatch):
    existing = CandidateSession(
        simulation_id=1,
        candidate_name="Jane",
        invite_email="jane@example.com",
        token="token",
        status="not_started",
        expires_at=datetime.now(UTC),
    )
    existing.id = 123

    class StubSession:
        def add(self, _obj):
            return None

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            raise IntegrityError("", {}, None)

    async def _get_existing(*_args, **_kwargs):
        return existing

    monkeypatch.setattr(
        sim_service.cs_repo, "get_by_simulation_and_email", _get_existing
    )
    cs, created = await sim_service.create_invite(
        StubSession(),
        simulation_id=1,
        payload=type(
            "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
        ),
        now=datetime.now(UTC),
    )
    assert cs.id == existing.id
    assert created is False


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_flow(async_session, monkeypatch):
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "templateKey": "python-fastapi",
        },
    )()
    user = type("U", (), {"company_id": 1, "id": 2})
    sim, tasks, scenario_job = await sim_service.create_simulation_with_tasks(
        async_session, payload, user
    )
    assert sim.id is not None
    assert sim.active_scenario_version_id is None
    assert sim.status == "generating"
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["simulationId"] == sim.id
    assert len(tasks) == len(sim_service.DEFAULT_5_DAY_BLUEPRINT)
    # ensure tasks are sorted and refreshed
    assert tasks[0].day_index == 1


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_enqueues_scenario_generation_job(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="sim-job@test.com")
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "companyContext": {"domain": "social", "productArea": "creator tools"},
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "AI may assist with scenario generation.",
                "evalEnabledByDay": {"1": True, "2": False, "9": True},
            },
            "templateKey": "python-fastapi",
        },
    )()

    sim, _tasks, scenario_job = await sim_service.create_simulation_with_tasks(
        async_session, payload, recruiter
    )

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as check_session:
        persisted_sim = (
            await check_session.execute(
                select(Simulation).where(Simulation.id == sim.id)
            )
        ).scalar_one()
        job = (
            await check_session.execute(
                select(Job).where(
                    Job.company_id == recruiter.company_id,
                    Job.job_type == "scenario_generation",
                    Job.idempotency_key == f"simulation:{sim.id}:scenario_generation",
                )
            )
        ).scalar_one()

    assert persisted_sim.id == sim.id
    assert scenario_job.id == job.id

    assert job.payload_json["simulationId"] == sim.id
    assert job.payload_json["templateKey"] == "python-fastapi"
    assert job.payload_json["scenarioTemplate"] == "default-5day-node-postgres"
    assert job.payload_json["recruiterContext"] == {
        "seniority": "mid",
        "focus": "Build",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "noticeText": "AI may assist with scenario generation.",
            "evalEnabledByDay": {"1": True, "2": False},
        },
    }


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_rejects_bad_template(async_session):
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "templateKey": "not-real",
        },
    )()
    user = type("U", (), {"company_id": 1, "id": 2})
    with pytest.raises(Exception) as excinfo:
        await sim_service.create_simulation_with_tasks(async_session, payload, user)
    assert excinfo.value.status_code == 422
    assert getattr(excinfo.value, "error_code", None) == "INVALID_TEMPLATE_KEY"
    assert "Invalid templateKey" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_create_invite_success(async_session):
    recruiter = await create_recruiter(async_session, email="invite-success@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    assert sim.active_scenario_version_id is not None
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    cs, created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert cs.token
    assert cs.status == "not_started"
    assert created is True


@pytest.mark.asyncio
async def test_create_invite_reuses_existing(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="reuse@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    first, created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert created is True
    first_id = first.id
    fail_once = True
    original_commit = async_session.commit

    async def _commit_with_integrity_error():
        nonlocal fail_once
        if fail_once:
            fail_once = False
            raise IntegrityError("", {}, None)
        return await original_commit()

    async def _get_existing(*_args, **_kwargs):
        return type("S", (), {"id": first_id})()

    monkeypatch.setattr(async_session, "commit", _commit_with_integrity_error)
    monkeypatch.setattr(
        sim_service.cs_repo, "get_by_simulation_and_email", _get_existing
    )
    second, created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert second.id == first_id
    assert created is False


@pytest.mark.asyncio
async def test_create_or_resend_invite_resends_active(async_session):
    recruiter = await create_recruiter(async_session, email="resend@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    first, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )

    second, outcome = await sim_service.create_or_resend_invite(
        async_session, simulation_id=sim.id, payload=payload, now=datetime.now(UTC)
    )

    assert second.id == first.id
    assert outcome == "resent"


@pytest.mark.asyncio
async def test_create_or_resend_invite_refreshes_expired(async_session):
    recruiter = await create_recruiter(async_session, email="expired@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    now = datetime.now(UTC)
    cs, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=now,
    )
    old_token = cs.token
    cs.expires_at = now - timedelta(days=1)
    await async_session.commit()

    refreshed, outcome = await sim_service.create_or_resend_invite(
        async_session, simulation_id=sim.id, payload=payload, now=now
    )

    assert refreshed.id == cs.id
    assert refreshed.token != old_token
    assert outcome == "created"


@pytest.mark.asyncio
async def test_create_or_resend_invite_rejects_completed(async_session):
    recruiter = await create_recruiter(async_session, email="completed@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    cs, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    cs.status = CANDIDATE_SESSION_STATUS_COMPLETED
    cs.completed_at = datetime.now(UTC)
    await async_session.commit()

    with pytest.raises(sim_service.InviteRejectedError) as excinfo:
        await sim_service.create_or_resend_invite(
            async_session, simulation_id=sim.id, payload=payload, now=datetime.now(UTC)
        )
    assert excinfo.value.outcome == "rejected"


@pytest.mark.asyncio
async def test_require_owned_simulation_success(async_session):
    recruiter = await create_recruiter(async_session, email="owned@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    owned = await sim_service.require_owned_simulation(
        async_session, sim.id, recruiter.id
    )
    assert owned.id == sim.id


@pytest.mark.asyncio
async def test_list_with_candidate_counts(async_session):
    recruiter = await create_recruiter(async_session, email="counts@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    rows = await sim_service.list_simulations(async_session, recruiter.id)
    assert rows[0][0].id == sim.id


@pytest.mark.asyncio
async def test_list_candidates_with_profile(async_session):
    recruiter = await create_recruiter(async_session, email="list@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=type("P", (), {"candidateName": "a", "inviteEmail": "b@example.com"}),
        scenario_version_id=sim.active_scenario_version_id,
    )
    rows = await sim_service.list_candidates_with_profile(async_session, sim.id)
    assert rows and rows[0][0].id == cs.id


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_invalid_template():
    payload = type(
        "Payload",
        (),
        {
            "title": "t",
            "role": "r",
            "techStack": "ts",
            "seniority": "s",
            "focus": "f",
            "templateKey": "invalid-key",
        },
    )()
    with pytest.raises(sim_service.ApiError):
        await sim_service.create_simulation_with_tasks(
            None, payload, SimpleNamespace(id=1, company_id=1)
        )


@pytest.mark.asyncio
async def test_require_owned_simulation_with_tasks_raises(monkeypatch):
    async def _return_none(*_a, **_k):
        return None, []

    monkeypatch.setattr(sim_service.sim_repo, "get_owned_with_tasks", _return_none)
    with pytest.raises(Exception) as excinfo:
        await sim_service.require_owned_simulation_with_tasks(None, 1, 2)
    assert excinfo.value.status_code == 404


def test_invite_is_expired_with_none():
    cs = SimpleNamespace(expires_at=None)
    assert sim_service._invite_is_expired(cs, now=datetime.now(UTC)) is False


@pytest.mark.asyncio
async def test_refresh_invite_token_retries_on_integrity(monkeypatch):
    class DummyDB:
        def __init__(self):
            self.calls = 0

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            self.calls += 1
            if self.calls == 1:
                raise IntegrityError("", "", "")

    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Retry",
        invite_email="retry@test.com",
        token="tok",
        status="not_started",
    )
    db = DummyDB()
    refreshed = await sim_service._refresh_invite_token(db, cs, now=datetime.now(UTC))
    assert refreshed.token != "tok"
    assert db.calls == 2


@pytest.mark.asyncio
async def test_create_or_resend_invite_rejects_completed_when_created(monkeypatch):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Done",
        invite_email="done@test.com",
        token="tok",
        status=CANDIDATE_SESSION_STATUS_COMPLETED,
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(db, simulation_id, payload, now=None):
        return cs, False

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    with pytest.raises(sim_service.InviteRejectedError):
        await sim_service.create_or_resend_invite(
            db=None,
            simulation_id=1,
            payload=SimpleNamespace(inviteEmail="done@test.com"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_require_owned_simulation_with_tasks_success(async_session):
    recruiter = await create_recruiter(async_session, email="owned@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    found_sim, found_tasks = await sim_service.require_owned_simulation_with_tasks(
        async_session, sim.id, recruiter.id
    )
    assert found_sim.id == sim.id
    assert [t.id for t in found_tasks] == [t.id for t in tasks]


@pytest.mark.asyncio
async def test_refresh_invite_token_exhausts_retries(monkeypatch):
    class DummyDB:
        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            raise IntegrityError("", "", "")

    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Retry",
        invite_email="retry@test.com",
        token="tok",
        status="not_started",
    )
    with pytest.raises(HTTPException):
        await sim_service._refresh_invite_token(DummyDB(), cs, now=datetime.now(UTC))


@pytest.mark.asyncio
async def test_create_or_resend_invite_existing_completed(monkeypatch):
    existing = CandidateSession(
        simulation_id=1,
        candidate_name="Done",
        invite_email="done@test.com",
        token="tok",
        status=CANDIDATE_SESSION_STATUS_COMPLETED,
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return existing

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    with pytest.raises(sim_service.InviteRejectedError):
        await sim_service.create_or_resend_invite(
            db=None,
            simulation_id=1,
            payload=SimpleNamespace(inviteEmail="done@test.com"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_create_or_resend_invite_refreshes_new_expired(monkeypatch):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Soon",
        invite_email="soon@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(db, simulation_id, payload, now=None):
        return cs, False

    class DummyDB:
        def __init__(self):
            self.commits = 0

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def refresh(self, obj):
            self.refreshed = obj

        async def flush(self):
            return None

    db = DummyDB()
    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    refreshed, outcome = await sim_service.create_or_resend_invite(
        db=db,
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="soon@test.com"),
        now=datetime.now(UTC),
    )
    assert refreshed is cs
    assert outcome == "created"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_create_or_resend_invite_returns_created_when_new(monkeypatch):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Fresh",
        invite_email="fresh@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(db, simulation_id, payload, now=None):
        return cs, True

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="fresh@test.com"),
        now=datetime.now(UTC),
    )
    assert outcome == "created"
    assert created is cs


@pytest.mark.asyncio
async def test_create_or_resend_invite_returns_resent_for_new_active(monkeypatch):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Active",
        invite_email="active@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(db, simulation_id, payload, now=None):
        return cs, False

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="active@test.com"),
        now=datetime.now(UTC),
    )
    assert outcome == "resent"
    assert created is cs


@pytest.mark.asyncio
async def test_create_or_resend_invite_passes_scenario_version_id(monkeypatch):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Scenario",
        invite_email="scenario@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    captured = {}

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(
        db, simulation_id, payload, now=None, scenario_version_id=None
    ):
        captured["scenario_version_id"] = scenario_version_id
        return cs, True

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="scenario@test.com"),
        now=datetime.now(UTC),
        scenario_version_id=321,
    )
    assert outcome == "created"
    assert created is cs
    assert captured["scenario_version_id"] == 321


@pytest.mark.asyncio
async def test_create_or_resend_invite_falls_back_when_create_invite_signature_is_legacy(
    monkeypatch,
):
    cs = CandidateSession(
        simulation_id=1,
        candidate_name="Legacy",
        invite_email="legacy@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    call_count = 0

    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite_legacy(db, simulation_id, payload, now=None):
        nonlocal call_count
        call_count += 1
        return cs, True

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite_legacy)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="legacy@test.com"),
        now=datetime.now(UTC),
        scenario_version_id=999,
    )
    assert outcome == "created"
    assert created is cs
    assert call_count == 1


@pytest.mark.asyncio
async def test_create_or_resend_invite_reraises_unrelated_typeerror(monkeypatch):
    async def fake_get_for_update(db, simulation_id, invite_email):
        return None

    async def fake_create_invite(db, simulation_id, payload, now=None):
        raise TypeError("unexpected internal typing issue")

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    with pytest.raises(TypeError):
        await sim_service.create_or_resend_invite(
            db=None,
            simulation_id=1,
            payload=SimpleNamespace(inviteEmail="typeerror@test.com"),
            now=datetime.now(UTC),
        )
