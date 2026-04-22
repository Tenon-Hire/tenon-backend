from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_claim_invite_allows_missing_email_verified_claim(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="verify-missing@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    principal = _principal(cs.invite_email, email_verified=None)

    verified = await cs_service.claim_invite_with_principal(
        async_session, cs.token, principal
    )
    assert verified.status == "in_progress"
    assert verified.candidate_auth0_sub == principal.sub
