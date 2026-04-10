from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_rejects_terminated_or_ineligible(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-rejects-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    scenario_v2 = await _create_scenario_version(
        async_session,
        trial_id=trial.id,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_GENERATING,
    )
    await async_session.commit()

    with pytest.raises(ApiError) as ineligible:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=trial.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="ineligible scenario",
            dry_run=False,
        )
    assert ineligible.value.status_code == 409
    assert ineligible.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE

    trial.status = TRIAL_STATUS_TERMINATED
    await async_session.commit()
    with pytest.raises(ApiError) as terminated:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=trial.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="terminated trial",
            dry_run=False,
        )
    assert terminated.value.status_code == 409
