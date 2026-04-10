from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_dry_run_is_non_mutating(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-dry-run-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    scenario_v2 = await _create_scenario_version(
        async_session,
        trial_id=trial.id,
        version_index=2,
    )
    trial_id = trial.id
    scenario_v2_id = scenario_v2.id
    prior_active = trial.active_scenario_version_id
    await async_session.commit()

    result = await admin_ops_service.use_trial_fallback_scenario(
        async_session,
        actor=_actor(),
        trial_id=trial_id,
        scenario_version_id=scenario_v2_id,
        apply_to="future_invites_only",
        reason="  dry   run fallback ",
        dry_run=True,
    )
    assert result.audit_id is None
    assert result.active_scenario_version_id == scenario_v2_id

    refreshed = await async_session.get(type(trial), trial_id)
    assert refreshed is not None
    assert refreshed.active_scenario_version_id == prior_active

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.action
                    == admin_ops_service.TRIAL_USE_FALLBACK_ACTION
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
