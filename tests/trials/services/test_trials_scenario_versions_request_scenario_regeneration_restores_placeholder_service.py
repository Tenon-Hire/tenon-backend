from __future__ import annotations

import pytest

from app.shared.database.shared_database_models_model import Job, ScenarioVersion
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.services import (
    trials_services_trials_scenario_versions_regeneration_service as regeneration_service,
)
from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_request_scenario_regeneration_restores_placeholder_and_enqueues_job(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-placeholder@test.com"
    )
    sim, _tasks = await _create_bare_trial(async_session, talent_partner)

    (
        updated_sim,
        regenerated,
        scenario_job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        trial_id=sim.id,
        actor_user_id=talent_partner.id,
    )

    assert updated_sim.active_scenario_version_id == regenerated.id
    assert updated_sim.pending_scenario_version_id is None
    assert updated_sim.status == "generating"
    assert regenerated.trial_id == sim.id
    assert regenerated.version_index == 1
    assert regenerated.status == "generating"
    assert regenerated.storyline_md == ""
    assert regenerated.project_brief_md == ""
    assert regenerated.task_prompts_json == []
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.status == JOB_STATUS_QUEUED
    assert scenario_job.payload_json["trialId"] == sim.id
    assert "scenarioVersionId" not in scenario_job.payload_json

    persisted_version = await async_session.get(ScenarioVersion, regenerated.id)
    persisted_job = await async_session.get(Job, scenario_job.id)
    assert persisted_version is not None
    assert persisted_job is not None


@pytest.mark.asyncio
async def test_request_scenario_regeneration_requeues_dead_letter_job(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-dead-letter@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    job = Job(
        job_type="scenario_generation",
        status=JOB_STATUS_DEAD_LETTER,
        idempotency_key=f"scenario_version:{sim.id}:scenario_generation",
        payload_json={"trialId": sim.id},
        company_id=sim.company_id,
        correlation_id=f"trial:{sim.id}",
        max_attempts=5,
    )
    async_session.add(job)
    await async_session.flush()

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()

    (
        updated_sim,
        regenerated,
        scenario_job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        trial_id=sim.id,
        actor_user_id=talent_partner.id,
    )

    assert updated_sim.active_scenario_version_id == regenerated.id
    assert scenario_job.id == job.id
    assert scenario_job.status == JOB_STATUS_QUEUED


@pytest.mark.asyncio
async def test_request_scenario_regeneration_propagates_unrelated_active_error(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-error@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)

    async def _raise_other_error(*_args, **_kwargs):
        raise ApiError(
            status_code=409,
            detail="boom",
            error_code="SCENARIO_OTHER_ERROR",
            retryable=False,
            details={},
        )

    monkeypatch.setattr(
        regeneration_service, "get_active_scenario_for_update", _raise_other_error
    )

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.request_scenario_regeneration(
            async_session,
            trial_id=sim.id,
            actor_user_id=talent_partner.id,
        )

    assert excinfo.value.error_code == "SCENARIO_OTHER_ERROR"
