from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_stored_sub_mismatch(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="stored-sub@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    cs.candidate_auth0_sub = "auth0|other"
    await async_session.commit()

    principal = _principal(cs.invite_email)
    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_owned_session(async_session, cs.id, principal)
    assert excinfo.value.status_code == 403
    assert (
        getattr(excinfo.value, "error_code", None)
        == "CANDIDATE_SESSION_ALREADY_CLAIMED"
    )
