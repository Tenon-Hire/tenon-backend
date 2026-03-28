from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_recording(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-recording@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="rec_999999",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recording asset not found"
