from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_from_draft_creates_submission_and_marks_draft(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-draft@test.com"
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

    day1_task = tasks[0]
    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="## Day 1 draft",
        content_json={"reflection": {"decisions": "use queue"}},
    )
    assert draft.finalized_submission_id is None

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )

    result = await finalize_handler.handle_day_close_finalize_text(
        _payload(
            candidate_session_id=candidate_session.id,
            task_id=day1_task.id,
            day_index=1,
            window_end_at=window_end_by_day[1],
        )
    )

    assert result["status"] == "created_submission"
    assert result["source"] == "draft"

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == day1_task.id,
            )
        )
    ).scalar_one()
    assert submission.content_text == "## Day 1 draft"
    assert submission.content_json == {"reflection": {"decisions": "use queue"}}

    finalized_draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert finalized_draft is not None
    assert finalized_draft.finalized_submission_id == submission.id
    assert finalized_draft.finalized_at is not None
