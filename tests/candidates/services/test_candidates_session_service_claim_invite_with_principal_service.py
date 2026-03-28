from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_claim_invite_with_principal(async_session):
    recruiter = await create_recruiter(async_session, email="verify@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="not_started"
    )
    principal = _principal(cs.invite_email)

    verified = await cs_service.claim_invite_with_principal(
        async_session, cs.token, principal
    )
    assert verified.status == "in_progress"
    assert verified.started_at is not None
    assert verified.candidate_auth0_sub == principal.sub
    assert verified.candidate_email == cs.invite_email
