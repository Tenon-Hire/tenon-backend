from __future__ import annotations

# helper import baseline for restructure-compat
from sqlalchemy import select

from tests.media.routes.media_handoff_upload_api_utils import (
    RecordingAsset,
    _fake_storage_provider,
)


async def _latest_recording(async_session, *, candidate_session_id: int, task_id: int):
    return (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session_id,
                    RecordingAsset.task_id == task_id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )


async def _init_and_complete_upload(
    async_client,
    async_session,
    *,
    task_id: int,
    candidate_session_id: int,
    headers: dict[str, str],
    size_bytes: int,
    filename: str,
):
    init_response = await async_client.post(
        f"/api/tasks/{task_id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": size_bytes,
            "filename": filename,
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = await _latest_recording(
        async_session,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
    assert recording is not None
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task_id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 200, complete_response.text
    return init_response, recording


__all__ = [name for name in globals() if not name.startswith("__")]
