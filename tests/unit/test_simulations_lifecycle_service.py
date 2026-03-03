from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.errors import ApiError
from app.domains import Company, Simulation, User
from app.domains.simulations import service as sim_service


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
