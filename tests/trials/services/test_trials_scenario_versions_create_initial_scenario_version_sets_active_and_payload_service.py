from __future__ import annotations

import pytest
from sqlalchemy import select

from app.evaluations.repositories import list_rubric_snapshots_for_scenario_version
from app.evaluations.services.evaluations_services_evaluations_winoe_rubric_snapshots_service import (
    WINOE_RUBRIC_REGISTRY,
)
from app.shared.database.shared_database_models_model import ScenarioVersion
from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_create_initial_scenario_version_sets_active_and_payload(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-init@test.com"
    )
    sim, tasks = await _create_bare_trial(async_session, talent_partner)

    scenario = await scenario_service.create_initial_scenario_version(
        async_session, trial=sim, tasks=tasks
    )

    assert scenario.version_index == 1
    assert scenario.status == "ready"
    assert sim.active_scenario_version_id == scenario.id
    assert scenario.task_prompts_json[0]["dayIndex"] == 1
    assert scenario.task_prompts_json[1]["dayIndex"] == 2

    persisted = await list_rubric_snapshots_for_scenario_version(
        async_session, scenario_version_id=scenario.id
    )
    assert len(persisted) == len(WINOE_RUBRIC_REGISTRY)
    reloaded = await async_session.scalar(
        select(ScenarioVersion).where(ScenarioVersion.id == scenario.id)
    )
    assert reloaded is not None
    assert reloaded.ai_policy_snapshot_json["snapshotDigest"]
