from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


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
        status=sim_service.SIMULATION_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(simulation)
    await async_session.flush()
    await _attach_active_scenario(async_session, simulation)
    simulation.status = sim_service.SIMULATION_STATUS_READY_FOR_REVIEW
    simulation.ready_for_review_at = datetime.now(UTC)
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
