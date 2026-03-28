from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_invalid_recording_id(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-invalid-id@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="not-a-recording-id",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "recordingId" in str(exc_info.value.detail)
