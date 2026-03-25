from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_no_draft_creates_empty_marker_submission(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="finalize-empty@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=False,
    )
    await async_session.commit()

    window_end_by_day = await _set_fully_closed_schedule(
        async_session,
        candidate_session=candidate_session,
    )
    day5_task = tasks[4]

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day5_task.id,
            day_index=5,
            window_end_at=window_end_by_day[5],
        )
    )

    assert result["status"] == "created_submission"
    assert result["source"] == "no_draft_marker"

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == day5_task.id,
            )
        )
    ).scalar_one()
    assert submission.content_text == ""
    assert submission.content_json == NO_DRAFT_AT_CUTOFF_MARKER
