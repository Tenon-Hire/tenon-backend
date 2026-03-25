from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_simulation_fallback_dry_run_is_non_mutating(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-dry-run-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
    )
    simulation_id = simulation.id
    scenario_v2_id = scenario_v2.id
    prior_active = simulation.active_scenario_version_id
    await async_session.commit()

    result = await admin_ops_service.use_simulation_fallback_scenario(
        async_session,
        actor=_actor(),
        simulation_id=simulation_id,
        scenario_version_id=scenario_v2_id,
        apply_to="future_invites_only",
        reason="  dry   run fallback ",
        dry_run=True,
    )
    assert result.audit_id is None
    assert result.active_scenario_version_id == scenario_v2_id

    refreshed = await async_session.get(type(simulation), simulation_id)
    assert refreshed is not None
    assert refreshed.active_scenario_version_id == prior_active

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.action
                    == admin_ops_service.SIMULATION_USE_FALLBACK_ACTION
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
