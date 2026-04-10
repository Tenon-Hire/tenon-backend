from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_is_idempotent_for_existing_v1(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="idempotent-scenario@test.com"
    )
    sim, _tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )

    first = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    second = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert first["status"] == "completed"
    assert second["status"] == "completed"

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        versions = (
            (
                await check_session.execute(
                    select(ScenarioVersion)
                    .where(ScenarioVersion.trial_id == sim.id)
                    .order_by(ScenarioVersion.version_index.asc())
                )
            )
            .scalars()
            .all()
        )
        refreshed_sim = await check_session.get(Trial, sim.id)
    assert len(versions) == 1
    assert versions[0].version_index == 1
    assert refreshed_sim is not None
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_sim.active_scenario_version_id == versions[0].id
