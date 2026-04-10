from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_updates_status(async_session):
    talent_partner = await create_talent_partner(async_session, email="promote@sim.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="not_started")
    principal = _principal(cs.invite_email)
    cs.candidate_auth0_sub = principal.sub
    cs.candidate_email = None
    await async_session.commit()

    refreshed = await cs_service.fetch_owned_session(async_session, cs.id, principal)
    assert refreshed.status == "in_progress"
    assert refreshed.candidate_auth0_email == principal.email
