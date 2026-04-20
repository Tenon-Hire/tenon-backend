from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_init_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-storage-error@test.com",
    )

    class _BrokenProvider(FakeStorageMediaProvider):
        def create_signed_upload_url(
            self,
            key: str,
            content_type: str,
            size_bytes: int,
            expires_seconds: int,
            duration_seconds: int | None = None,
        ) -> str:
            del key, content_type, size_bytes, expires_seconds, duration_seconds
            raise StorageMediaError("storage down")

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=_BrokenProvider(),
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Media storage unavailable"
    assert getattr(exc_info.value, "error_code", None) == MEDIA_STORAGE_UNAVAILABLE
