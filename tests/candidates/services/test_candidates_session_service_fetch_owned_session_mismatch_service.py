from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_mismatch(async_session):
    recruiter = await create_recruiter(async_session, email="mismatch@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    principal = _principal("other@example.com")
    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_owned_session(async_session, cs.id, principal)
    assert excinfo.value.status_code == 403
    assert (
        getattr(excinfo.value, "error_code", None) == "CANDIDATE_INVITE_EMAIL_MISMATCH"
    )
