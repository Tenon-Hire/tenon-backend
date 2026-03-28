from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_by_token_expired(async_session):
    recruiter = await create_recruiter(async_session, email="expire@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        expires_in_days=-1,
    )
    now = datetime.now(UTC)
    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_by_token(async_session, cs.token, now=now)
    assert excinfo.value.status_code == 410
