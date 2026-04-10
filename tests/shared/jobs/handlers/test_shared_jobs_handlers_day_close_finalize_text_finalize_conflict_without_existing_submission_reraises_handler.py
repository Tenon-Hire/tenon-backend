from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_conflict_without_existing_submission_reraises(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-conflict-raise@test.com"
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
    await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=day1_task.id,
        content_text="draft",
        content_json={"k": "v"},
    )

    async def _none_existing(*_args, **_kwargs):
        return None

    async def _raise_conflict(*_args, **_kwargs):
        raise finalize_handler.SubmissionConflict()

    monkeypatch.setattr(
        finalize_handler,
        "async_session_maker",
        _session_maker(async_session),
    )
    monkeypatch.setattr(finalize_handler, "_get_existing_submission", _none_existing)
    monkeypatch.setattr(
        finalize_handler.submission_service,
        "create_submission",
        _raise_conflict,
    )

    with pytest.raises(finalize_handler.SubmissionConflict):
        await finalize_handler.handle_day_close_finalize_text(
            _payload(
                candidate_session_id=candidate_session.id,
                task_id=day1_task.id,
                day_index=1,
                window_end_at=window_end_by_day[1],
            )
        )
