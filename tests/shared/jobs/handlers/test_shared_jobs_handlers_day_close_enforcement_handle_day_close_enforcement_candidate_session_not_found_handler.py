from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_candidate_session_not_found(
    async_session,
    monkeypatch,
):
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": 999999,
            "taskId": 1,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "candidate_session_not_found"
