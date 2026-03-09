from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains import Job
from app.jobs import worker
from app.repositories.jobs.models import JOB_STATUS_SUCCEEDED
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


async def _create_simulation_via_api(
    async_client,
    async_session: AsyncSession,
    headers: dict[str, str],
) -> dict:
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
    created = res.json()
    assert created["status"] == "generating"
    assert created["scenarioGenerationJobId"]

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=_session_maker(async_session),
            worker_id="sim-lifecycle-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    scenario_job = await async_session.get(Job, created["scenarioGenerationJobId"])
    assert scenario_job is not None
    assert scenario_job.status == JOB_STATUS_SUCCEEDED
    return created


@pytest.mark.asyncio
async def test_activate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner-lifecycle@test.com")
    outsider = await create_recruiter(
        async_session, email="outsider-lifecycle@test.com"
    )
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
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
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
    sim_id = created["id"]

    res = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": False},
    )
    assert res.status_code == 400
    assert res.json()["errorCode"] == "SIMULATION_CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_activate_nonexistent_returns_404(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="missing-lifecycle@test.com")

    missing = await async_client.post(
        "/api/simulations/999999/activate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Simulation not found"


@pytest.mark.asyncio
async def test_terminate_is_owner_only_and_idempotent(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner-term@test.com")
    outsider = await create_recruiter(async_session, email="outsider-term@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
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
        json={"confirm": True, "reason": "regenerate"},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "terminated"
    assert first_body["terminatedAt"] is not None
    assert len(first_body["cleanupJobIds"]) == 1
    first_job_id = first_body["cleanupJobIds"][0]

    jobs_after_first = (
        await async_session.execute(
            select(Job).where(Job.job_type == "simulation_cleanup")
        )
    ).scalars()
    matching_first = [
        job
        for job in jobs_after_first
        if isinstance(job.payload_json, dict)
        and job.payload_json.get("simulationId") == sim_id
    ]
    assert len(matching_first) == 1
    assert matching_first[0].id == first_job_id
    assert matching_first[0].job_type == "simulation_cleanup"
    assert matching_first[0].idempotency_key == f"simulation_cleanup:{sim_id}"
    assert matching_first[0].payload_json["reason"] == "regenerate"

    second = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(owner),
        json={"confirm": True},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "terminated"
    assert second_body["terminatedAt"] == first_body["terminatedAt"]
    assert second_body["cleanupJobIds"] == first_body["cleanupJobIds"]

    jobs_after_second = (
        await async_session.execute(
            select(Job).where(Job.job_type == "simulation_cleanup")
        )
    ).scalars()
    matching_second = [
        job
        for job in jobs_after_second
        if isinstance(job.payload_json, dict)
        and job.payload_json.get("simulationId") == sim_id
    ]
    assert len(matching_second) == 1
    assert matching_second[0].id == first_job_id


@pytest.mark.asyncio
async def test_invite_requires_active_inviting(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="invite-state@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
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
async def test_invite_create_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="invite-stop@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    blocked = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "SIMULATION_TERMINATED"


@pytest.mark.asyncio
async def test_invite_resend_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="resend-stop@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
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
    candidate_session_id = invite.json()["candidateSessionId"]

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    resend = await async_client.post(
        f"/api/simulations/{sim_id}/candidates/{candidate_session_id}/invite/resend",
        headers=auth_header_factory(recruiter),
    )
    assert resend.status_code == 409, resend.text
    assert resend.json()["errorCode"] == "SIMULATION_TERMINATED"


@pytest.mark.asyncio
async def test_terminated_hidden_by_default_in_simulation_and_candidate_lists(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="filter@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
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
async def test_candidate_token_resolve_and_claim_hidden_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="token-hide@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
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
        json={"candidateName": "Jane Doe", "inviteEmail": "hidden@example.com"},
    )
    assert invite.status_code == 200, invite.text
    token = invite.json()["token"]

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    resolve = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": "Bearer candidate:hidden@example.com"},
    )
    assert resolve.status_code == 404, resolve.text
    assert resolve.json()["detail"] == "Invalid invite token"

    claim = await async_client.post(
        f"/api/candidate/session/{token}/claim",
        headers={"Authorization": "Bearer candidate:hidden@example.com"},
    )
    assert claim.status_code == 404, claim.text
    assert claim.json()["detail"] == "Invalid invite token"


@pytest.mark.asyncio
async def test_detail_includes_status_and_lifecycle_timestamps(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="detail-lifecycle@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
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
