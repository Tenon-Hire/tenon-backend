from __future__ import annotations

from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
)
from app.media.repositories.recordings import repository as recordings_repo


async def _complete_handoff_upload(
    *,
    async_client,
    async_session,
    candidate_session,
    task_id: int,
    filename: str,
    size_bytes: int,
) -> str:
    headers = {
        "Authorization": f"Bearer candidate:{candidate_session.invite_email}",
        "x-candidate-session-id": str(candidate_session.id),
    }
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
    recording_id = init_response.json()["recordingId"]
    recording = await recordings_repo.get_latest_for_task_session(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task_id,
    )
    assert recording is not None
    storage_provider = get_storage_media_provider()
    assert isinstance(storage_provider, FakeStorageMediaProvider)
    storage_provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task_id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text
    return recording_id


__all__ = [name for name in globals() if not name.startswith("__")]
