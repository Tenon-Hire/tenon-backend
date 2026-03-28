from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


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
        status=sim_service.SIMULATION_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.flush()
    await _attach_active_scenario(async_session, simulation)
    simulation.status = sim_service.SIMULATION_STATUS_TERMINATED
    simulation.terminated_at = datetime.now(UTC)
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await sim_service.activate_simulation(
            async_session,
            simulation_id=simulation.id,
            actor_user_id=owner.id,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"
