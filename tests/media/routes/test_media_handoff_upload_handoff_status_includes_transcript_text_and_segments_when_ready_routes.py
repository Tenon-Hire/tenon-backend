from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_includes_transcript_text_and_segments_when_ready(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-status-ready@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_536,
            "filename": "status-ready.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    transcript = await transcripts_repo.get_by_recording_id(async_session, recording.id)
    assert transcript is not None
    await transcripts_repo.update_transcript(
        async_session,
        transcript=transcript,
        status=TRANSCRIPT_STATUS_READY,
        text="ready transcript text",
        segments_json=[
            {"startMs": 0, "endMs": 1250, "text": "ready"},
            {"startMs": 1250, "endMs": 2500, "text": "transcript"},
        ],
        model_name="mock-stt-v1",
        commit=True,
    )

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == recording_id
    assert body["recording"]["downloadUrl"] is not None
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_READY
    assert body["transcript"]["text"] == "ready transcript text"
    assert body["transcript"]["segments"] == [
        {"id": None, "startMs": 0, "endMs": 1250, "text": "ready"},
        {"id": None, "startMs": 1250, "endMs": 2500, "text": "transcript"},
    ]
