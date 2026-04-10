from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_no_draft_creates_empty_marker_submission(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-empty@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
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
