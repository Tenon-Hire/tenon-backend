from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_by_token_terminated_trial_hidden(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="term-fetch@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    sim.status = TRIAL_STATUS_TERMINATED
    await async_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_by_token(async_session, cs.token)
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"
