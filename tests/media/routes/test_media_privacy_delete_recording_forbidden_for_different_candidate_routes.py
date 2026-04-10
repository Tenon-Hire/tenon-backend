from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_different_candidate(
    async_client,
    async_session,
    candidate_header_factory,
):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-delete-auth@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="delete-owner@test.com",
        status="in_progress",
    )
    other_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="delete-other@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        filename="forbidden-same-company.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(other_session),
    )

    assert response.status_code == 403
