from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_rejects_non_ready_scenario_status(async_session):
    recruiter = await create_recruiter(
        async_session, email="scenario-patch-not-ready-status@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    sim.status = "ready_for_review"
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "draft"
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.patch_scenario_version(
            async_session,
            simulation_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=recruiter.id,
            updates={"focus_notes": "Should be blocked"},
        )
    assert excinfo.value.error_code == "SCENARIO_NOT_EDITABLE"

    audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit).where(
                    ScenarioEditAudit.scenario_version_id == active.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
