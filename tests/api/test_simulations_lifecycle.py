from __future__ import annotations

import pytest

from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


async def _create_simulation_via_api(async_client, headers: dict[str, str]) -> dict:
    res = await async_client.post(
        "/api/simulations",
        headers=headers,
        json={
            "title": "Lifecycle Sim",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI",
            "seniority": "Mid",
            "focus": "Lifecycle behavior",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_activate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner-lifecycle@test.com")
    outsider = await create_recruiter(
        async_session, email="outsider-lifecycle@test.com"
    )
    created = await _create_simulation_via_api(async_client, auth_header_factory(owner))
    sim_id = created["id"]

    forbidden = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(outsider),
        json={"confirm": True},
    )
    assert forbidden.status_code == 403

    first = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "active_inviting"
    assert first_body["activatedAt"] is not None

    second = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "active_inviting"
    assert second_body["activatedAt"] == first_body["activatedAt"]


@pytest.mark.asyncio
async def test_activate_requires_confirm_true(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="confirm-lifecycle@test.com")
    created = await _create_simulation_via_api(async_client, auth_header_factory(owner))
    sim_id = created["id"]

    res = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": False},
    )
    assert res.status_code == 400
    assert res.json()["errorCode"] == "SIMULATION_CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_terminate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner-term@test.com")
    outsider = await create_recruiter(async_session, email="outsider-term@test.com")
    created = await _create_simulation_via_api(async_client, auth_header_factory(owner))
    sim_id = created["id"]

    forbidden = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(outsider),
        json={"confirm": True},
    )
    assert forbidden.status_code == 403

    first = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "terminated"
    assert first_body["terminatedAt"] is not None

    second = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "terminated"
    assert second_body["terminatedAt"] == first_body["terminatedAt"]


@pytest.mark.asyncio
async def test_invite_requires_active_inviting(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="invite-state@test.com")
    created = await _create_simulation_via_api(
        async_client, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    blocked = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json() == {
        "detail": "Simulation is not approved for inviting.",
        "errorCode": "SIMULATION_NOT_INVITABLE",
        "retryable": False,
        "details": {"status": "ready_for_review"},
    }

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    allowed = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert allowed.status_code == 200, allowed.text


@pytest.mark.asyncio
async def test_terminated_hidden_by_default_in_simulation_and_candidate_lists(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="filter@test.com")
    created = await _create_simulation_via_api(
        async_client, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert invite.status_code == 200, invite.text

    terminated = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    simulations_default = await async_client.get(
        "/api/simulations", headers=auth_header_factory(recruiter)
    )
    assert simulations_default.status_code == 200, simulations_default.text
    assert all(row["id"] != sim_id for row in simulations_default.json())

    simulations_including = await async_client.get(
        "/api/simulations?includeTerminated=true",
        headers=auth_header_factory(recruiter),
    )
    assert simulations_including.status_code == 200, simulations_including.text
    assert any(row["id"] == sim_id for row in simulations_including.json())

    candidates_default = await async_client.get(
        f"/api/simulations/{sim_id}/candidates",
        headers=auth_header_factory(recruiter),
    )
    assert candidates_default.status_code == 404

    candidates_including = await async_client.get(
        f"/api/simulations/{sim_id}/candidates?includeTerminated=true",
        headers=auth_header_factory(recruiter),
    )
    assert candidates_including.status_code == 200, candidates_including.text
    assert len(candidates_including.json()) == 1


@pytest.mark.asyncio
async def test_candidate_invites_hide_terminated_by_default(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="candidate-filter@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="candidate-filter@example.com",
    )
    await async_session.commit()

    terminated = await async_client.post(
        f"/api/simulations/{simulation.id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    default_invites = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert default_invites.status_code == 200, default_invites.text
    assert default_invites.json() == []

    include_terminated = await async_client.get(
        "/api/candidate/invites?includeTerminated=true",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert include_terminated.status_code == 200, include_terminated.text
    rows = include_terminated.json()
    assert len(rows) == 1
    assert rows[0]["candidateSessionId"] == candidate_session.id


@pytest.mark.asyncio
async def test_detail_includes_status_and_lifecycle_timestamps(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="detail-lifecycle@test.com")
    created = await _create_simulation_via_api(
        async_client, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    detail = await async_client.get(
        f"/api/simulations/{sim_id}",
        headers=auth_header_factory(recruiter),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "ready_for_review"
    assert body["generatingAt"] is not None
    assert body["readyForReviewAt"] is not None
    assert body["activatedAt"] is None
    assert body["scenarioVersionSummary"]["templateKey"] == "python-fastapi"

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    detail_after = await async_client.get(
        f"/api/simulations/{sim_id}",
        headers=auth_header_factory(recruiter),
    )
    assert detail_after.status_code == 200, detail_after.text
    body_after = detail_after.json()
    assert body_after["status"] == "active_inviting"
    assert body_after["activatedAt"] is not None
