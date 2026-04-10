from __future__ import annotations

import pytest

from app.trials.services import scenario_generation
from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_request_scenario_regeneration_enqueues_targeted_job(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-job@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    previous_active = sim.active_scenario_version_id

    (
        updated_sim,
        regenerated,
        scenario_job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        trial_id=sim.id,
        actor_user_id=talent_partner.id,
    )

    assert regenerated.status == "generating"
    assert regenerated.version_index == 2
    assert updated_sim.active_scenario_version_id == previous_active
    assert updated_sim.pending_scenario_version_id == regenerated.id
    assert scenario_job.job_type == "scenario_generation"
    assert scenario_job.payload_json["trialId"] == sim.id
    assert scenario_job.payload_json["scenarioVersionId"] == regenerated.id

    persisted = await async_session.get(Job, scenario_job.id)
    assert persisted is not None
    assert (
        persisted.max_attempts
        == scenario_generation.SCENARIO_GENERATION_JOB_MAX_ATTEMPTS
    )
    assert (
        persisted.idempotency_key
        == f"scenario_version:{regenerated.id}:scenario_generation"
    )

    with pytest.raises(ApiError) as duplicate_exc:
        await scenario_service.request_scenario_regeneration(
            async_session,
            trial_id=sim.id,
            actor_user_id=talent_partner.id,
        )
    assert duplicate_exc.value.status_code == 409
    assert duplicate_exc.value.error_code == "SCENARIO_REGENERATION_PENDING"
