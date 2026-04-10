from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_not_found_and_editability_guards(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-guards-extra@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None

    with pytest.raises(HTTPException) as not_found:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=999999,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert not_found.value.status_code == 404

    sim.status = "generating"
    await async_session.commit()
    with pytest.raises(ApiError) as sim_status_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert sim_status_exc.value.error_code == "SCENARIO_NOT_EDITABLE"
    sim_status_audits = (
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
    assert sim_status_audits == []

    sim.status = "ready_for_review"
    active.status = "draft"
    await async_session.commit()
    with pytest.raises(ApiError) as scenario_status_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert scenario_status_exc.value.error_code == "SCENARIO_NOT_EDITABLE"
    scenario_status_audits = (
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
    assert scenario_status_audits == []

    active.status = "generating"
    await async_session.commit()
    with pytest.raises(ApiError) as scenario_status_generating_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert scenario_status_generating_exc.value.error_code == "SCENARIO_NOT_EDITABLE"
    scenario_status_generating_audits = (
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
    assert scenario_status_generating_audits == []
