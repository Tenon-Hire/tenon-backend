from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_recruiter_token(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-recruiter@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="delete-owner-recruiter@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        filename="forbidden-recruiter.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(
            owner_session,
            token=f"recruiter:{recruiter.email}",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Candidate access required"
