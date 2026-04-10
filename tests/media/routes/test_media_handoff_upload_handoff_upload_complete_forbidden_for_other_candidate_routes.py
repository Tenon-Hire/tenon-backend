from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_complete_forbidden_for_other_candidate(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-owner@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session_a = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="candidate-a@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    candidate_session_b = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="candidate-b@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session_a),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 512,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]

    forbidden = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=candidate_header_factory(candidate_session_b),
        json={"recordingId": recording_id},
    )
    assert forbidden.status_code == 403
