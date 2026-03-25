from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_task_not_found(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(async_session, email="task-missing@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
    )
    await async_session.commit()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await enforcement_handler.handle_day_close_enforcement(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": 999999,
            "dayIndex": 2,
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    )
    assert result["status"] == "task_not_found"
