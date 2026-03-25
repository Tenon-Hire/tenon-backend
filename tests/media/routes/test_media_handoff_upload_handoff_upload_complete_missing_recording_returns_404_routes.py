from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_missing_recording_returns_404(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-missing@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=candidate_header_factory(candidate_session),
        json={"recordingId": "rec_999999"},
    )
    assert response.status_code == 404
