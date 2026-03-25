from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_content_type_mismatch(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-type-mismatch@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type="video/webm",
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Uploaded object content type does not match expected contentType"
    )
