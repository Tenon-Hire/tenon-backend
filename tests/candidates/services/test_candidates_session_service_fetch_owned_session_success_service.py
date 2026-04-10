from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_success(async_session):
    talent_partner = await create_talent_partner(async_session, email="ok2@sim.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    principal = _principal(cs.invite_email)
    loaded = await cs_service.fetch_owned_session(async_session, cs.id, principal)
    assert loaded.id == cs.id
