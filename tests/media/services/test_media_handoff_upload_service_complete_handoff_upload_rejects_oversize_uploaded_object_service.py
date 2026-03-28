from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_oversize_uploaded_object(
    async_session,
    monkeypatch,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-size-oversize@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 1024)
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes + 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 413
    assert getattr(exc_info.value, "error_code", None) == REQUEST_TOO_LARGE
