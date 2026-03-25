from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_requires_candidate_session_headers(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="handoff-status-auth@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    await async_session.commit()

    response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers={"x-candidate-token": "candidate:missing-header@test.com"},
    )
    assert response.status_code == 401
    assert "detail" in response.json()
