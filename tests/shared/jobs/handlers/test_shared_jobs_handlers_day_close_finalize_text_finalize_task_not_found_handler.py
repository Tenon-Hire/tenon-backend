from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_task_not_found(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="finalize-task404@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=False,
    )
    await async_session.commit()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        {
            "candidateSessionId": candidate_session.id,
            "taskId": 999999,
            "dayIndex": 1,
            "windowEndAt": "2026-03-10T18:30:00Z",
        }
    )
    assert result["status"] == "task_not_found"
