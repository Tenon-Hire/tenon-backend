from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_simulation_fallback_wrong_or_missing_targets(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-missing-owner@test.com"
    )
    simulation_a, _ = await create_simulation(async_session, created_by=recruiter)
    simulation_b, _ = await create_simulation(async_session, created_by=recruiter)
    other_simulation_scenario = await _create_scenario_version(
        async_session,
        simulation_id=simulation_b.id,
        version_index=2,
    )
    await async_session.commit()

    with pytest.raises(HTTPException) as wrong_simulation:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation_a.id,
            scenario_version_id=other_simulation_scenario.id,
            apply_to="future_invites_only",
            reason="wrong simulation scenario",
            dry_run=False,
        )
    assert wrong_simulation.value.status_code == 404

    with pytest.raises(HTTPException) as missing_simulation:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=999_999,
            scenario_version_id=other_simulation_scenario.id,
            apply_to="future_invites_only",
            reason="missing simulation",
            dry_run=False,
        )
    assert missing_simulation.value.status_code == 404

    with pytest.raises(HTTPException) as missing_scenario:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation_a.id,
            scenario_version_id=999_999,
            apply_to="future_invites_only",
            reason="missing scenario",
            dry_run=False,
        )
    assert missing_scenario.value.status_code == 404
