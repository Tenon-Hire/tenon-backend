from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_wrong_or_missing_targets(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-missing-owner@test.com"
    )
    trial_a, _ = await create_trial(async_session, created_by=talent_partner)
    trial_b, _ = await create_trial(async_session, created_by=talent_partner)
    other_trial_scenario = await _create_scenario_version(
        async_session,
        trial_id=trial_b.id,
        version_index=2,
    )
    await async_session.commit()

    with pytest.raises(HTTPException) as wrong_trial:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=trial_a.id,
            scenario_version_id=other_trial_scenario.id,
            apply_to="future_invites_only",
            reason="wrong trial scenario",
            dry_run=False,
        )
    assert wrong_trial.value.status_code == 404

    with pytest.raises(HTTPException) as missing_trial:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=999_999,
            scenario_version_id=other_trial_scenario.id,
            apply_to="future_invites_only",
            reason="missing trial",
            dry_run=False,
        )
    assert missing_trial.value.status_code == 404

    with pytest.raises(HTTPException) as missing_scenario:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=trial_a.id,
            scenario_version_id=999_999,
            apply_to="future_invites_only",
            reason="missing scenario",
            dry_run=False,
        )
    assert missing_scenario.value.status_code == 404
