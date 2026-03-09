from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domains import CandidateSession, ScenarioVersion, Simulation
from app.jobs import worker
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
async def test_regenerate_creates_next_version_and_switches_active(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-regen@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first_invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
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
    assert first_scenario.locked_at is not None

    regenerate = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=auth_header_factory(recruiter),
    )
    assert regenerate.status_code == 200, regenerate.text
    regenerated_scenario = regenerate.json()["scenario"]
    assert regenerated_scenario["versionIndex"] == 2
    assert regenerated_scenario["status"] == "ready"
    assert regenerated_scenario["lockedAt"] is None
    assert regenerated_scenario["id"] != first_scenario_id

    second_invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
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
    assert second_candidate_session.scenario_version_id == regenerated_scenario["id"]

    refreshed_first = await async_session.get(ScenarioVersion, first_scenario_id)
    refreshed_second = await async_session.get(
        ScenarioVersion, regenerated_scenario["id"]
    )
    assert refreshed_first is not None
    assert refreshed_first.status == "locked"
    assert refreshed_first.locked_at is not None
    assert refreshed_second is not None
    assert refreshed_second.status == "locked"
    assert refreshed_second.locked_at is not None

    versions = (
        (
            await async_session.execute(
                select(ScenarioVersion)
                .where(ScenarioVersion.simulation_id == sim_id)
                .order_by(ScenarioVersion.version_index.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [version.version_index for version in versions] == [1, 2]


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
