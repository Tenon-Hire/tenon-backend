from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


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
        status=sim_service.SIMULATION_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.flush()
    await _attach_active_scenario(async_session, simulation)
    simulation.status = sim_service.SIMULATION_STATUS_READY_FOR_REVIEW
    simulation.ready_for_review_at = datetime.now(UTC)
    await async_session.commit()

    with pytest.raises(HTTPException) as forbidden:
        await sim_service.require_owner_for_lifecycle(
            async_session,
            simulation_id=simulation.id,
            actor_user_id=other.id,
        )
    assert forbidden.value.status_code == 403
