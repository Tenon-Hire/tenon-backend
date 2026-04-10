from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_pending_approval_blocked(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-pending-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    scenario_v2 = await _create_scenario_version(
        async_session,
        trial_id=trial.id,
        version_index=2,
    )
    trial.pending_scenario_version_id = scenario_v2.id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.use_trial_fallback_scenario(
            async_session,
            actor=_actor(),
            trial_id=trial.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="pending approval blocked",
            dry_run=False,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"
