from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.errors import ApiError
from app.domains import Company, Job, Simulation, User
from app.domains.simulations import service as sim_service
from app.services.simulations import lifecycle as lifecycle_service


def _simulation(status: str) -> Simulation:
    return Simulation(
        company_id=1,
        title="Lifecycle",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Test",
        scenario_template="default-5day-node-postgres",
        created_by=1,
        status=status,
    )


def test_normalize_simulation_status_strictness():
    assert (
        sim_service.normalize_simulation_status("active")
        == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    )
    assert (
        sim_service.normalize_simulation_status(sim_service.SIMULATION_STATUS_DRAFT)
        == sim_service.SIMULATION_STATUS_DRAFT
    )
    assert sim_service.normalize_simulation_status("unknown_status") is None
    assert sim_service.normalize_simulation_status(None) is None


def test_normalize_simulation_status_or_raise_valid_value():
    assert (
        sim_service.normalize_simulation_status_or_raise("active")
        == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    )


def test_normalize_simulation_status_or_raise_invalid_value():
    with pytest.raises(ApiError) as excinfo:
        sim_service.normalize_simulation_status_or_raise("unknown_status")
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "SIMULATION_STATUS_INVALID"
    assert excinfo.value.details == {"status": "unknown_status"}


def test_apply_status_transition_allows_happy_path():
    sim = _simulation(sim_service.SIMULATION_STATUS_DRAFT)
    at = datetime.now(UTC)

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.SIMULATION_STATUS_GENERATING,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.SIMULATION_STATUS_GENERATING
    assert sim.generating_at == at

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.SIMULATION_STATUS_READY_FOR_REVIEW,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.SIMULATION_STATUS_READY_FOR_REVIEW
    assert sim.ready_for_review_at == at

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.SIMULATION_STATUS_ACTIVE_INVITING,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    assert sim.activated_at == at


def test_apply_status_transition_rejects_invalid_edges():
    sim = _simulation(sim_service.SIMULATION_STATUS_DRAFT)
    with pytest.raises(ApiError) as excinfo:
        sim_service.apply_status_transition(
            sim,
            target_status=sim_service.SIMULATION_STATUS_ACTIVE_INVITING,
            changed_at=datetime.now(UTC),
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"
    assert excinfo.value.details["allowedTransitions"] == [
        sim_service.SIMULATION_STATUS_GENERATING
    ]


def test_apply_status_transition_terminate_and_idempotency():
    now = datetime.now(UTC)
    sim = _simulation(sim_service.SIMULATION_STATUS_READY_FOR_REVIEW)
    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.SIMULATION_STATUS_TERMINATED,
        changed_at=now,
    )
    assert changed is True
    assert sim.status == sim_service.SIMULATION_STATUS_TERMINATED
    assert sim.terminated_at == now

    unchanged = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.SIMULATION_STATUS_TERMINATED,
        changed_at=datetime.now(UTC),
    )
    assert unchanged is False
    assert sim.terminated_at == now


def test_apply_status_transition_rejects_unknown_target():
    sim = _simulation(sim_service.SIMULATION_STATUS_READY_FOR_REVIEW)
    with pytest.raises(ValueError):
        sim_service.apply_status_transition(sim, target_status="unsupported_status")


def test_apply_status_transition_terminate_rejects_unknown_current_status():
    sim = _simulation("legacy_unknown")
    with pytest.raises(ApiError) as excinfo:
        sim_service.apply_status_transition(
            sim,
            target_status=sim_service.SIMULATION_STATUS_TERMINATED,
            changed_at=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"


def test_require_simulation_invitable_terminated_raises_specific_error():
    sim = _simulation(sim_service.SIMULATION_STATUS_TERMINATED)
    with pytest.raises(ApiError) as excinfo:
        sim_service.require_simulation_invitable(sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_TERMINATED"


@pytest.mark.asyncio
async def test_activate_and_terminate_service_idempotency(async_session):
    company = Company(name="Lifecycle Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-lifecycle-service@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    simulation = Simulation(
        company_id=company.id,
        title="Lifecycle",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Service idempotency",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.SIMULATION_STATUS_READY_FOR_REVIEW,
        ready_for_review_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.commit()

    activated = await sim_service.activate_simulation(
        async_session,
        simulation_id=simulation.id,
        actor_user_id=owner.id,
    )
    assert activated.status == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    assert activated.activated_at is not None
    first_activated_at = activated.activated_at

    activated_again = await sim_service.activate_simulation(
        async_session,
        simulation_id=simulation.id,
        actor_user_id=owner.id,
    )
    assert activated_again.status == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    assert activated_again.activated_at == first_activated_at

    terminated = await sim_service.terminate_simulation(
        async_session,
        simulation_id=simulation.id,
        actor_user_id=owner.id,
    )
    assert terminated.status == sim_service.SIMULATION_STATUS_TERMINATED
    assert terminated.terminated_at is not None
    first_terminated_at = terminated.terminated_at

    terminated_again = await sim_service.terminate_simulation(
        async_session,
        simulation_id=simulation.id,
        actor_user_id=owner.id,
    )
    assert terminated_again.status == sim_service.SIMULATION_STATUS_TERMINATED
    assert terminated_again.terminated_at == first_terminated_at


@pytest.mark.asyncio
async def test_require_owner_for_lifecycle_not_found_and_forbidden(async_session):
    company = Company(name="Lifecycle Guard Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-guard@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    other = User(
        name="Other",
        email="other-guard@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add_all([owner, other])
    await async_session.flush()

    with pytest.raises(HTTPException) as missing:
        await sim_service.require_owner_for_lifecycle(
            async_session,
            simulation_id=999999,
            actor_user_id=owner.id,
        )
    assert missing.value.status_code == 404

    simulation = Simulation(
        company_id=company.id,
        title="Lifecycle Guard",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Guard coverage",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.SIMULATION_STATUS_READY_FOR_REVIEW,
        ready_for_review_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.commit()

    with pytest.raises(HTTPException) as forbidden:
        await sim_service.require_owner_for_lifecycle(
            async_session,
            simulation_id=simulation.id,
            actor_user_id=other.id,
        )
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_activate_rejected_transition_surfaces_api_error(async_session):
    company = Company(name="Activate Reject Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-activate-reject@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    simulation = Simulation(
        company_id=company.id,
        title="Already Terminated",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Rejected transition",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.SIMULATION_STATUS_TERMINATED,
        terminated_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await sim_service.activate_simulation(
            async_session,
            simulation_id=simulation.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_terminate_with_cleanup_sets_reason_and_enqueues_job(async_session):
    company = Company(name="Terminate Cleanup Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-terminate-cleanup@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    simulation = Simulation(
        company_id=company.id,
        title="Terminate with cleanup",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Termination metadata",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.SIMULATION_STATUS_READY_FOR_REVIEW,
        ready_for_review_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.commit()

    result = await sim_service.terminate_simulation_with_cleanup(
        async_session,
        simulation_id=simulation.id,
        actor_user_id=owner.id,
        reason="regenerate",
    )
    assert result.simulation.status == sim_service.SIMULATION_STATUS_TERMINATED
    assert result.simulation.terminated_reason == "regenerate"
    assert result.simulation.terminated_by_recruiter_id == owner.id
    assert len(result.cleanup_job_ids) == 1

    job_rows = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == "simulation_cleanup",
                Job.idempotency_key == f"simulation_cleanup:{simulation.id}",
            )
        )
    ).scalars()
    jobs = list(job_rows)
    assert len(jobs) == 1
    assert jobs[0].id == result.cleanup_job_ids[0]
    assert jobs[0].payload_json["simulationId"] == simulation.id
    assert jobs[0].payload_json["reason"] == "regenerate"


@pytest.mark.asyncio
async def test_terminate_with_cleanup_rethrows_transition_errors(
    async_session, monkeypatch
):
    company = Company(name="Terminate Error Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-terminate-error@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    simulation = Simulation(
        company_id=company.id,
        title="Terminate Error",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Transition failure",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.SIMULATION_STATUS_READY_FOR_REVIEW,
        ready_for_review_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.commit()

    def _raise_transition(*_args, **_kwargs):
        raise ApiError(
            status_code=409,
            detail="invalid",
            error_code="SIMULATION_INVALID_STATUS_TRANSITION",
            retryable=False,
        )

    monkeypatch.setattr(lifecycle_service, "apply_status_transition", _raise_transition)

    with pytest.raises(ApiError) as excinfo:
        await sim_service.terminate_simulation_with_cleanup(
            async_session,
            simulation_id=simulation.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"
