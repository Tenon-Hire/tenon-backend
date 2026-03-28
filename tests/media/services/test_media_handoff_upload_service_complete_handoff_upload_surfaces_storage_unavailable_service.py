from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-storage-error@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=256,
        filename="demo.mp4",
        storage_provider=provider,
    )

    class _BrokenMetadataProvider(FakeStorageMediaProvider):
        def get_object_metadata(self, key: str):
            del key
            raise StorageMediaError("down")

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=_BrokenMetadataProvider(),
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Media storage unavailable"
    assert getattr(exc_info.value, "error_code", None) == MEDIA_STORAGE_UNAVAILABLE
