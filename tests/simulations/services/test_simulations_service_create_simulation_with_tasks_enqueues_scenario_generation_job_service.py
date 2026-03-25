from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_simulation_with_tasks_enqueues_scenario_generation_job(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="sim-job@test.com")
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "companyContext": {"domain": "social", "productArea": "creator tools"},
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "AI may assist with scenario generation.",
                "evalEnabledByDay": {"1": True, "2": False, "9": True},
            },
            "templateKey": "python-fastapi",
        },
    )()

    sim, _tasks, scenario_job = await sim_service.create_simulation_with_tasks(
        async_session, payload, recruiter
    )

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as check_session:
        persisted_sim = (
            await check_session.execute(
                select(Simulation).where(Simulation.id == sim.id)
            )
        ).scalar_one()
        job = (
            await check_session.execute(
                select(Job).where(
                    Job.company_id == recruiter.company_id,
                    Job.job_type == "scenario_generation",
                    Job.idempotency_key == f"simulation:{sim.id}:scenario_generation",
                )
            )
        ).scalar_one()

    assert persisted_sim.id == sim.id
    assert scenario_job.id == job.id

    assert job.payload_json["simulationId"] == sim.id
    assert job.payload_json["templateKey"] == "python-fastapi"
    assert job.payload_json["scenarioTemplate"] == "default-5day-node-postgres"
    assert job.payload_json["recruiterContext"] == {
        "seniority": "mid",
        "focus": "Build",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "noticeText": "AI may assist with scenario generation.",
            "evalEnabledByDay": {
                "1": True,
                "2": False,
                "3": True,
                "4": True,
                "5": True,
            },
        },
    }
