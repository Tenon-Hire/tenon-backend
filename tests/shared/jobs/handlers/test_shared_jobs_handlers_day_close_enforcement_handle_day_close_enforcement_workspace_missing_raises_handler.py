from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_workspace_missing_raises(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="workspace-missing@test.com"
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    day2_task = next(task for task in tasks if task.day_index == 2)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )

    with pytest.raises(RuntimeError):
        await enforcement_handler.handle_day_close_enforcement(
            {
                "candidateSessionId": candidate_session.id,
                "taskId": day2_task.id,
                "dayIndex": 2,
                "windowEndAt": "2026-03-10T21:00:00Z",
            }
        )
