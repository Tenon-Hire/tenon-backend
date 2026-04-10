from __future__ import annotations

import pytest

from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_status_storage_failure_degrades_to_null_download_url(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-status-storage-failure@test.com"
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
            "sizeBytes": 1_024,
            "filename": "status-storage-failure.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
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
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 200, complete_response.text

    provider = _fake_storage_provider()

    def _raise_storage_error(*args, **kwargs):
        del args, kwargs
        raise StorageMediaError("storage down")

    monkeypatch.setattr(provider, "create_signed_download_url", _raise_storage_error)

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == init_response.json()["recordingId"]
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING
