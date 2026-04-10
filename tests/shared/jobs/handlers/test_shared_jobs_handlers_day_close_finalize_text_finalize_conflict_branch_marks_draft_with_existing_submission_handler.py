from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_conflict_branch_marks_draft_with_existing_submission(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-conflict@test.com"
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

    existing_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=day1_task,
        content_text="manual",
    )
    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="draft",
        content_json={"k": "v"},
    )

    call_count = {"n": 0}

    async def _fake_get_existing(*_args, **_kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return existing_submission

    async def _raise_conflict(*_args, **_kwargs):
        raise finalize_handler.SubmissionConflict()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    monkeypatch.setattr(
        finalize_handler, "_get_existing_submission", _fake_get_existing
    )
    monkeypatch.setattr(
        finalize_handler.submission_service,
        "create_submission",
        _raise_conflict,
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
    assert result["submissionId"] == existing_submission.id
    assert result["source"] == "draft"
    draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
    )
    assert draft is not None
    assert draft.finalized_submission_id == existing_submission.id
