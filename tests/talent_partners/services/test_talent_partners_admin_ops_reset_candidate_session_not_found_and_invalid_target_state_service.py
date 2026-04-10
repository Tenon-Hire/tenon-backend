from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_not_found_and_invalid_target_state(
    async_session,
):
    with pytest.raises(HTTPException) as missing:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=999_999,
            target_state="claimed",
            reason="missing session",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert missing.value.status_code == 404

    talent_partner = await create_talent_partner(
        async_session, email="reset-invalid-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="not_started",
        candidate_auth0_sub="auth0|candidate-reset-invalid",
        claimed_at=datetime.now(UTC),
    )
    await async_session.commit()

    with pytest.raises(ValueError):
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="invalid_state",  # type: ignore[arg-type]
            reason="invalid target",
            override_if_evaluated=False,
            dry_run=False,
        )
