from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_skips_invalid_payload():
    result = await finalize_handler.handle_day_close_finalize_text(
        {"candidateSessionId": "abc", "taskId": 0}
    )
    assert result["status"] == "skipped_invalid_payload"
