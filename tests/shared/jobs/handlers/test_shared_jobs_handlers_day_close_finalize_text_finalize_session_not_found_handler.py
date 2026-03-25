from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_session_not_found(async_session, monkeypatch):
    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        {
            "candidateSessionId": 999999,
            "taskId": 123,
            "dayIndex": 1,
            "windowEndAt": "2026-03-10T18:30:00Z",
        }
    )
    assert result["status"] == "candidate_session_not_found"
