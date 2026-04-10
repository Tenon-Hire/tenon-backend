from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_failed_attempts_do_not_append_audit_rows(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-no-audit-on-failure@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "ready_for_review"
    await async_session.commit()
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None

    await scenario_service.patch_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=talent_partner.id,
        updates={"focus_notes": "Baseline successful edit"},
    )
    initial_audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit)
                .where(ScenarioEditAudit.scenario_version_id == active.id)
                .order_by(ScenarioEditAudit.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(initial_audits) == 1

    with pytest.raises(ApiError) as validation_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"task_prompts_json": [{"dayIndex": 2, "title": "Missing desc"}]},
        )
    assert validation_exc.value.error_code == "SCENARIO_PATCH_INVALID"

    active.status = "draft"
    await async_session.commit()
    with pytest.raises(ApiError) as status_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "Blocked by status"},
        )
    assert status_exc.value.error_code == "SCENARIO_NOT_EDITABLE"

    active.status = "ready"
    active.locked_at = datetime.now(UTC)
    await async_session.commit()
    with pytest.raises(ApiError) as locked_exc:
        await scenario_service.patch_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=active.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "Blocked by lock"},
        )
    assert locked_exc.value.error_code == "SCENARIO_LOCKED"

    final_audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit)
                .where(ScenarioEditAudit.scenario_version_id == active.id)
                .order_by(ScenarioEditAudit.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(final_audits) == 1
