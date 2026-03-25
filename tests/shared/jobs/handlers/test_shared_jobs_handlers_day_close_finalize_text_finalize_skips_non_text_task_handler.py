from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_skips_non_text_task(async_session, monkeypatch):
    recruiter = await create_recruiter(async_session, email="finalize-nontext@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=False,
    )
    tasks[0].type = "code"
    await async_session.commit()
    window_end_by_day = await _set_fully_closed_schedule(
        async_session,
        candidate_session=candidate_session,
    )

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=tasks[0].id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )
    assert result["status"] == "skipped_non_text_task"
