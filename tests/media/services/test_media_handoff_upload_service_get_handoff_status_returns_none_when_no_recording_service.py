from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_get_handoff_status_returns_none_when_no_recording(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-status-empty@test.com",
    )
    recording, transcript = await get_handoff_status(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
    )
    assert recording is None
    assert transcript is None
