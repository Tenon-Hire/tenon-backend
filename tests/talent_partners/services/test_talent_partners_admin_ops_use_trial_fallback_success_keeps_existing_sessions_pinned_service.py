from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_success_keeps_existing_sessions_pinned(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-success-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    existing_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="existing-pinned@test.com",
    )
    scenario_v1_id = existing_session.scenario_version_id
    scenario_v2 = await _create_scenario_version(
        async_session,
        trial_id=trial.id,
        version_index=2,
    )
    await async_session.commit()

    result = await admin_ops_service.use_trial_fallback_scenario(
        async_session,
        actor=_actor(),
        trial_id=trial.id,
        scenario_version_id=scenario_v2.id,
        apply_to="future_invites_only",
        reason="  switch to   fallback v2 ",
        dry_run=False,
    )
    assert result.active_scenario_version_id == scenario_v2.id
    assert result.audit_id is not None

    refreshed_existing = await async_session.get(
        type(existing_session), existing_session.id
    )
    assert refreshed_existing is not None
    assert refreshed_existing.scenario_version_id == scenario_v1_id

    refreshed_trial = await async_session.get(type(trial), trial.id)
    assert refreshed_trial is not None
    await async_session.refresh(refreshed_trial)
    new_session = await create_candidate_session(
        async_session,
        trial=refreshed_trial,
        invite_email="new-future@test.com",
    )
    await async_session.commit()
    assert new_session.scenario_version_id == scenario_v2.id

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "switch to fallback v2"
    assert audit.payload_json["noOp"] is False
    assert audit.payload_json["previousActiveScenarioVersionId"] == scenario_v1_id
