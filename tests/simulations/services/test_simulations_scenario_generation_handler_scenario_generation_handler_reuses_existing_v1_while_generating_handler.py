from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_reuses_existing_v1_while_generating(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="existing-v1-generating@test.com"
    )
    sim, _tasks, _job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )

    existing_v1 = _build_scenario_version(
        sim,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md="stale storyline",
    )
    async_session.add(existing_v1)
    await async_session.commit()

    first = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert first["status"] == "completed"
    assert first["scenarioVersionId"] == existing_v1.id

    first_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.simulation_id == sim.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
    ]

    second = await scenario_handler.handle_scenario_generation({"simulationId": sim.id})
    assert second["status"] == "completed"
    assert second["scenarioVersionId"] == existing_v1.id

    second_task_snapshot = [
        (task.day_index, task.title, task.description, task.max_score)
        for task in (
            (
                await async_session.execute(
                    select(Task)
                    .where(Task.simulation_id == sim.id)
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
                    .where(ScenarioVersion.simulation_id == sim.id)
                    .order_by(ScenarioVersion.version_index.asc())
                )
            )
            .scalars()
            .all()
        )
        refreshed_sim = await check_session.get(Simulation, sim.id)
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
        {"simulationId": sim.id}
    )
    assert moved_result == {
        "status": "skipped_active_version_moved",
        "simulationId": sim.id,
        "activeScenarioVersionId": moved_active.id,
    }
