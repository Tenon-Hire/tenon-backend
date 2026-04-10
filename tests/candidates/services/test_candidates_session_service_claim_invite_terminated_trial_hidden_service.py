from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_claim_invite_terminated_trial_hidden(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="term-claim@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    sim.status = TRIAL_STATUS_TERMINATED
    await async_session.commit()
    principal = _principal(cs.invite_email)

    with pytest.raises(HTTPException) as excinfo:
        await cs_service.claim_invite_with_principal(async_session, cs.token, principal)
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"
