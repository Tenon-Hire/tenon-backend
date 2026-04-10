from __future__ import annotations

import pytest

from app.trials.services import scenario_generation
from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_tasks_enqueues_scenario_generation_job(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="sim-job@test.com"
    )
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

    sim, _tasks, scenario_job = await sim_service.create_trial_with_tasks(
        async_session, payload, talent_partner
    )

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as check_session:
        persisted_sim = (
            await check_session.execute(select(Trial).where(Trial.id == sim.id))
        ).scalar_one()
        job = (
            await check_session.execute(
                select(Job).where(
                    Job.company_id == talent_partner.company_id,
                    Job.job_type == "scenario_generation",
                    Job.idempotency_key == f"trial:{sim.id}:scenario_generation",
                )
            )
        ).scalar_one()

    assert persisted_sim.id == sim.id
    assert scenario_job.id == job.id
    assert job.max_attempts == scenario_generation.SCENARIO_GENERATION_JOB_MAX_ATTEMPTS

    assert job.payload_json["trialId"] == sim.id
    assert job.payload_json["templateKey"] == "python-fastapi"
    assert job.payload_json["scenarioTemplate"] == "python-fastapi"
    assert job.payload_json["talentPartnerContext"] == {
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
