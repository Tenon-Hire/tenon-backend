from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_trial_fallback_same_scenario_is_noop_with_audit(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fallback-noop-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    await async_session.commit()

    result = await admin_ops_service.use_trial_fallback_scenario(
        async_session,
        actor=_actor(),
        trial_id=trial.id,
        scenario_version_id=trial.active_scenario_version_id or 0,
        apply_to="future_invites_only",
        reason=" no-op    fallback ",
        dry_run=False,
    )
    assert result.audit_id is not None
    assert result.active_scenario_version_id == trial.active_scenario_version_id

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "no-op fallback"
    assert audit.payload_json["noOp"] is True
