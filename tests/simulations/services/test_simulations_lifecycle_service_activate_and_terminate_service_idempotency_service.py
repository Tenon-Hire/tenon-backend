from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


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
        status=sim_service.SIMULATION_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.flush()
    await _attach_active_scenario(async_session, simulation)
    simulation.status = sim_service.SIMULATION_STATUS_READY_FOR_REVIEW
    simulation.ready_for_review_at = datetime.now(UTC)
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
