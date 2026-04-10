from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_manual_submit_precedence_is_noop(async_session, monkeypatch):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-manual@test.com"
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

    manual_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=day1_task,
        content_text="manual submit",
        content_json={"manual": True},
    )
    await async_session.commit()

    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="late draft",
        content_json={"draft": True},
    )

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

    assert result["status"] == "no_op_existing_submission"
    assert result["submissionId"] == manual_submission.id

    same_submission = (
        await async_session.execute(
            select(Submission).where(Submission.id == manual_submission.id)
        )
    ).scalar_one()
    assert same_submission.content_text == "manual submit"
    assert same_submission.content_json == {"manual": True}

    draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert draft is not None
    assert draft.finalized_submission_id == manual_submission.id
