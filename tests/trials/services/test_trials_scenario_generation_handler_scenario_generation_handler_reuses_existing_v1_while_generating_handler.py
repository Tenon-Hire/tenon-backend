from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_reuses_existing_v1_while_generating(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="existing-v1-generating@test.com"
    )
    sim, _tasks, _job = await create_trial_with_tasks(
        async_session,
        _trial_payload(),
        talent_partner,
    )

    existing_v1 = _build_scenario_version(
        sim,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md="stale storyline",
    )
    async_session.add(existing_v1)
    await async_session.commit()

    first = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert first["status"] == "completed"
    assert first["scenarioVersionId"] == existing_v1.id

    first_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.trial_id == sim.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    ]

    second = await scenario_handler.handle_scenario_generation({"trialId": sim.id})
    assert second["status"] == "completed"
    assert second["scenarioVersionId"] == existing_v1.id

    second_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.trial_id == sim.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    ]
    assert second_task_snapshot == first_task_snapshot

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
    assert versions[0].id == existing_v1.id

    assert refreshed_sim is not None
    assert refreshed_sim.status == "ready_for_review"
    assert refreshed_sim.active_scenario_version_id == existing_v1.id

    moved_active = _build_scenario_version(
        sim,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md="moved",
    )
    async_session.add(moved_active)
    await async_session.flush()
    sim.active_scenario_version_id = moved_active.id
    await async_session.commit()

    moved_result = await scenario_handler.handle_scenario_generation(
        {"trialId": sim.id}
    )
    assert moved_result == {
        "status": "skipped_active_version_moved",
        "trialId": sim.id,
        "activeScenarioVersionId": moved_active.id,
    }
