from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_skips_non_code_task(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="non-code-task@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    day1_task = next(task for task in tasks if task.day_index == 1)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
    )
    await async_session.commit()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": day1_task.id,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "skipped_non_code_task"
    assert result["dayIndex"] == 1
