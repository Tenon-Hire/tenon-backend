from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.routers import simulations as sim_routes
from app.core.settings import settings
from app.domains import CandidateSession, Job, ScenarioVersion, Simulation
from app.jobs import worker
from app.repositories.jobs.models import JOB_STATUS_QUEUED
from tests.factories import create_recruiter


async def _create_simulation(
    async_client, async_session, headers: dict[str, str]
) -> int:
    response = await async_client.post(
        "/api/simulations",
        headers=headers,
        json={
            "title": "Scenario Version Sim",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI",
            "seniority": "mid",
            "focus": "Scenario lock semantics",
        },
    )
    assert response.status_code == 201, response.text
    simulation_id = int(response.json()["id"])
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="scenario-versions-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    return simulation_id


@pytest.mark.asyncio
async def test_first_invite_locks_active_scenario_and_pins_candidate_session(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-lock@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    detail_before = await async_client.get(
        f"/api/simulations/{sim_id}", headers=auth_header_factory(recruiter)
    )
    assert detail_before.status_code == 200, detail_before.text
    scenario_before = detail_before.json()["scenario"]
    assert scenario_before["versionIndex"] == 1
    assert scenario_before["status"] == "ready"
    assert scenario_before["lockedAt"] is None

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane-lock@example.com"},
    )
    assert invite.status_code == 200, invite.text
    body = invite.json()

    detail_after = await async_client.get(
        f"/api/simulations/{sim_id}", headers=auth_header_factory(recruiter)
    )
    assert detail_after.status_code == 200, detail_after.text
    scenario_after = detail_after.json()["scenario"]
    assert scenario_after["id"] == scenario_before["id"]
    assert scenario_after["status"] == "locked"
    assert scenario_after["lockedAt"] is not None

    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(
                CandidateSession.id == body["candidateSessionId"]
            )
        )
    ).scalar_one()
    assert candidate_session.scenario_version_id == scenario_before["id"]


@pytest.mark.asyncio
async def test_regenerate_requires_approval_and_preserves_existing_pinning(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-regen@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first_invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=headers,
        json={"candidateName": "First", "inviteEmail": "first@example.com"},
    )
    assert first_invite.status_code == 200, first_invite.text
    first_candidate_session_id = first_invite.json()["candidateSessionId"]

    first_scenario = (
        await async_session.execute(
            select(ScenarioVersion)
            .join(
                Simulation,
                Simulation.active_scenario_version_id == ScenarioVersion.id,
            )
            .where(Simulation.id == sim_id)
        )
    ).scalar_one()
    first_scenario_id = first_scenario.id
    assert first_scenario.version_index == 1
    assert first_scenario.status == "locked"
    initial_detail = await async_client.get(
        f"/api/simulations/{sim_id}", headers=headers
    )
    assert initial_detail.status_code == 200, initial_detail.text
    initial_body = initial_detail.json()
    assert initial_body["status"] == "active_inviting"
    assert initial_body["activeScenarioVersionId"] == first_scenario_id
    assert initial_body["pendingScenarioVersionId"] is None

    regenerate = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    regenerated_payload = regenerate.json()
    regenerated_scenario_id = regenerated_payload["scenarioVersionId"]
    assert regenerated_payload["status"] == "generating"
    assert isinstance(regenerated_payload["jobId"], str)
    assert regenerated_scenario_id != first_scenario_id

    queued_job = (
        await async_session.execute(
            select(ScenarioVersion).where(ScenarioVersion.id == regenerated_scenario_id)
        )
    ).scalar_one()
    assert queued_job.status == "generating"

    detail_pending = await async_client.get(
        f"/api/simulations/{sim_id}", headers=headers
    )
    assert detail_pending.status_code == 200, detail_pending.text
    pending_body = detail_pending.json()
    assert pending_body["status"] == "ready_for_review"
    assert pending_body["activeScenarioVersionId"] == first_scenario_id
    assert pending_body["pendingScenarioVersionId"] == regenerated_scenario_id

    activate_while_pending = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate_while_pending.status_code == 409, activate_while_pending.text
    assert activate_while_pending.json()["errorCode"] == "SCENARIO_APPROVAL_PENDING"

    blocked_invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=headers,
        json={"candidateName": "Blocked", "inviteEmail": "blocked@example.com"},
    )
    assert blocked_invite.status_code == 409, blocked_invite.text
    assert blocked_invite.json()["errorCode"] == "SCENARIO_APPROVAL_PENDING"

    approve_early = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/{regenerated_scenario_id}/approve",
        headers=headers,
    )
    assert approve_early.status_code == 409, approve_early.text
    assert approve_early.json()["errorCode"] == "SCENARIO_NOT_READY"

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="scenario-versions-regen-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async_session.expire_all()
    refreshed_regenerated = await async_session.get(
        ScenarioVersion, regenerated_scenario_id
    )
    assert refreshed_regenerated is not None
    assert refreshed_regenerated.status == "ready"
    detail_ready = await async_client.get(f"/api/simulations/{sim_id}", headers=headers)
    assert detail_ready.status_code == 200, detail_ready.text
    ready_body = detail_ready.json()
    assert ready_body["status"] == "ready_for_review"
    assert ready_body["activeScenarioVersionId"] == first_scenario_id
    assert ready_body["pendingScenarioVersionId"] == regenerated_scenario_id

    approve = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/{regenerated_scenario_id}/approve",
        headers=headers,
    )
    assert approve.status_code == 200, approve.text
    approve_body = approve.json()
    assert approve_body["status"] == "active_inviting"
    assert approve_body["activeScenarioVersionId"] == regenerated_scenario_id
    assert approve_body["pendingScenarioVersionId"] is None
    detail_approved = await async_client.get(
        f"/api/simulations/{sim_id}", headers=headers
    )
    assert detail_approved.status_code == 200, detail_approved.text
    approved_detail_body = detail_approved.json()
    assert approved_detail_body["status"] == "active_inviting"
    assert approved_detail_body["activeScenarioVersionId"] == regenerated_scenario_id
    assert approved_detail_body["pendingScenarioVersionId"] is None

    second_invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=headers,
        json={"candidateName": "Second", "inviteEmail": "second@example.com"},
    )
    assert second_invite.status_code == 200, second_invite.text
    second_candidate_session_id = second_invite.json()["candidateSessionId"]

    first_candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(
                CandidateSession.id == first_candidate_session_id
            )
        )
    ).scalar_one()
    second_candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(
                CandidateSession.id == second_candidate_session_id
            )
        )
    ).scalar_one()
    assert first_candidate_session.scenario_version_id == first_scenario_id
    assert second_candidate_session.scenario_version_id == regenerated_scenario_id


@pytest.mark.asyncio
async def test_regenerate_duplicate_pending_returns_409(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-duplicate@test.com"
    )
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert second.status_code == 409, second.text
    assert second.json()["errorCode"] == "SCENARIO_REGENERATION_PENDING"


@pytest.mark.asyncio
async def test_regenerate_owner_and_not_found_guards(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="scenario-owner@test.com")
    outsider = await create_recruiter(async_session, email="scenario-outsider@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(owner)
    )

    forbidden = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=auth_header_factory(outsider),
    )
    assert forbidden.status_code == 403, forbidden.text

    missing = await async_client.post(
        "/api/simulations/999999/scenario/regenerate",
        headers=auth_header_factory(owner),
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.asyncio
async def test_mutating_locked_scenario_returns_scenario_locked(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-mutate@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Locked", "inviteEmail": "locked@example.com"},
    )
    assert invite.status_code == 200, invite.text

    mutate = await async_client.patch(
        f"/api/simulations/{sim_id}/scenario/active",
        headers=auth_header_factory(recruiter),
        json={"focusNotes": "This should fail"},
    )
    assert mutate.status_code == 409, mutate.text
    assert mutate.json() == {
        "detail": "Scenario version is locked.",
        "errorCode": "SCENARIO_LOCKED",
    }


@pytest.mark.asyncio
async def test_regenerate_enqueues_scenario_generation_job(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-job-queue@test.com"
    )
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)
    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    regenerate = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    payload = regenerate.json()

    job = await async_session.get(Job, payload["jobId"])
    assert job is not None
    assert job.status == JOB_STATUS_QUEUED
    assert job.payload_json["simulationId"] == sim_id
    assert job.payload_json["scenarioVersionId"] == payload["scenarioVersionId"]


@pytest.mark.asyncio
async def test_regenerate_rate_limited_in_prod(
    async_client, async_session, auth_header_factory, monkeypatch
):
    monkeypatch.setattr(settings, "ENV", "prod")
    sim_routes.rate_limit.limiter.reset()
    original_rule = sim_routes.SCENARIO_REGENERATE_RATE_LIMIT
    sim_routes.SCENARIO_REGENERATE_RATE_LIMIT = sim_routes.rate_limit.RateLimitRule(
        limit=1, window_seconds=60.0
    )

    try:
        recruiter = await create_recruiter(
            async_session, email="scenario-regen-rate@test.com"
        )
        headers = auth_header_factory(recruiter)
        first_sim_id = await _create_simulation(async_client, async_session, headers)
        second_sim_id = await _create_simulation(async_client, async_session, headers)

        activate_first = await async_client.post(
            f"/api/simulations/{first_sim_id}/activate",
            headers=headers,
            json={"confirm": True},
        )
        assert activate_first.status_code == 200, activate_first.text
        activate_second = await async_client.post(
            f"/api/simulations/{second_sim_id}/activate",
            headers=headers,
            json={"confirm": True},
        )
        assert activate_second.status_code == 200, activate_second.text

        first = await async_client.post(
            f"/api/simulations/{first_sim_id}/scenario/regenerate",
            headers=headers,
        )
        assert first.status_code == 200, first.text

        second = await async_client.post(
            f"/api/simulations/{second_sim_id}/scenario/regenerate",
            headers=headers,
        )
        assert second.status_code == 429, second.text
    finally:
        sim_routes.SCENARIO_REGENERATE_RATE_LIMIT = original_rule
        sim_routes.rate_limit.limiter.reset()
