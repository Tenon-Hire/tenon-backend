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
            "preferredLanguageFramework": "Python",
            "seniority": "Mid",
            "focus": "Build",
            "companyContext": {
                "domain": "social",
                "productArea": "creator tools",
                "preferredLanguageFramework": "Python",
            },
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "AI may assist with scenario generation.",
                "evalEnabledByDay": {"1": True, "2": False, "9": True},
            },
        },
    )()

    sim, _tasks, scenario_job = await trial_service.create_trial_with_tasks(
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
    assert "templateKey" not in job.payload_json
    assert "scenarioTemplate" not in job.payload_json
    assert job.payload_json["talentPartnerContext"] == {
        "seniority": "mid",
        "focus": "Build",
        "companyContext": {
            "domain": "social",
            "productArea": "creator tools",
            "preferredLanguageFramework": "Python",
        },
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


@pytest.mark.asyncio
async def test_create_trial_with_tasks_accepts_pivoted_payload(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="sim-job-pivot@test.com"
    )
    payload = type(
        "P",
        (),
        {
            "title": "Title",
            "role": "Role",
            "seniority": "Mid",
            "preferredLanguageFramework": "Python/FastAPI",
            "companyContext": {"domain": "social"},
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "AI may assist with scenario generation.",
                "evalEnabledByDay": {"1": True},
            },
        },
    )()

    sim, _tasks, scenario_job = await trial_service.create_trial_with_tasks(
        async_session, payload, talent_partner
    )

    assert sim.tech_stack == ""
    assert sim.focus == ""
    assert sim.company_context == {
        "domain": "social",
        "preferredLanguageFramework": "Python/FastAPI",
    }
    assert scenario_job.payload_json["talentPartnerContext"]["companyContext"] == {
        "domain": "social",
        "preferredLanguageFramework": "Python/FastAPI",
    }
