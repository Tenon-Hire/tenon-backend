from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_candidate_delete_recording_is_idempotent_and_blocks_recruiter_download(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-api@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2048,
            "filename": "delete-me.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_public_id = init_response.json()["recordingId"]

    recording = await _latest_recording(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert recording is not None
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_public_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    submission = await _submission_for_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert submission is not None

    recruiter_before_delete = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert recruiter_before_delete.status_code == 200, recruiter_before_delete.text
    assert recruiter_before_delete.json()["recording"]["downloadUrl"] is not None

    delete_first = await async_client.post(
        f"/api/recordings/{recording_public_id}/delete",
        headers=headers,
    )
    assert delete_first.status_code == 200, delete_first.text
    assert delete_first.json() == {"status": "deleted"}

    delete_second = await async_client.post(
        f"/api/recordings/{recording_public_id}/delete",
        headers=headers,
    )
    assert delete_second.status_code == 200, delete_second.text
    assert delete_second.json() == {"status": "deleted"}

    recruiter_after_delete = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert recruiter_after_delete.status_code == 200, recruiter_after_delete.text
    body = recruiter_after_delete.json()
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"] is None

    candidate_status = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert candidate_status.status_code == 200, candidate_status.text
    status_payload = candidate_status.json()
    assert status_payload["recording"]["status"] == "deleted"
    assert status_payload["recording"]["downloadUrl"] is None
    assert status_payload["transcript"] is None
