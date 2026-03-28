from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_init_handoff_upload_rejects_non_handoff_task(async_session):
    _, non_handoff_task, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-not-handoff@test.com",
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=non_handoff_task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "handoff tasks" in str(exc_info.value.detail)
