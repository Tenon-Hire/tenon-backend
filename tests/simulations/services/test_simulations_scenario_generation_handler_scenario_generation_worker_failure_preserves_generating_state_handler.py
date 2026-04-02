from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_worker_failure_preserves_generating_state(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="fail-scenario@test.com")
    sim, _tasks, job = await create_simulation_with_tasks(
        async_session,
        _simulation_payload(),
        recruiter,
    )
    job.max_attempts = 1
    await async_session.commit()

    def _explode(**_kwargs):
        raise RuntimeError("forced scenario generation failure")

    monkeypatch.setattr(scenario_handler, "generate_scenario_payload", _explode)

    worker.register_builtin_handlers()
    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="scenario-failure-worker",
        now=datetime.now(UTC),
    )
    assert handled is True

    session_maker = _session_maker(async_session)
    async with session_maker() as check_session:
        refreshed_sim = await check_session.get(Simulation, sim.id)
        refreshed_job = await jobs_repo.get_by_id(check_session, job.id)
    assert refreshed_sim is not None
    assert refreshed_job is not None

    assert refreshed_sim.status == "generating"
    assert refreshed_sim.active_scenario_version_id is None
    assert refreshed_job.status == JOB_STATUS_DEAD_LETTER
    assert "forced scenario generation failure" in (refreshed_job.last_error or "")

    versions = (
        (
            await async_session.execute(
                select(ScenarioVersion).where(ScenarioVersion.simulation_id == sim.id)
            )
        )
        .scalars()
        .all()
    )
    assert versions == []
