from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_invalid_payload():
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": "abc",
            "taskId": 10,
            "dayIndex": 2,
        }
    )
    assert result["status"] == "skipped_invalid_payload"
    assert result["candidateSessionId"] is None
