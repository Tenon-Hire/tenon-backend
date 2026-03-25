from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_by_token_terminated_simulation_hidden(async_session):
    recruiter = await create_recruiter(async_session, email="term-fetch@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    sim.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_by_token(async_session, cs.token)
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"
