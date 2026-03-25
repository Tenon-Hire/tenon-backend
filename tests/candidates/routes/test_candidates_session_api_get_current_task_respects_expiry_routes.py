from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_get_current_task_respects_expiry(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="expired@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        expires_in_days=-1,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(days=2),
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 410
