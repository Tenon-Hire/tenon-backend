from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.shared.database.shared_database_models_model import CandidateSession
from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


@pytest.mark.asyncio
async def test_finalize_day5_from_draft_completes_session(async_session, monkeypatch):
    talent_partner = await create_talent_partner(
        async_session, email="finalize-day5-complete@test.com"
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
    for task in tasks[:4]:
        await create_submission(
            async_session,
            candidate_session=candidate_session,
            task=task,
            content_text=f"day{task.day_index}",
        )
    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks[4].id,
        content_text="## Day 5 draft",
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
            task_id=tasks[4].id,
            day_index=5,
            window_end_at=window_end_by_day[5],
        )
    )

    assert result["status"] == "created_submission"
    assert result["source"] == "draft"

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == tasks[4].id,
            )
        )
    ).scalar_one()
    assert submission.content_text == "## Day 5 draft"
    assert submission.content_json == {"reflection": {"decisions": "use queue"}}

    finalized_draft = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks[4].id,
    )
    assert finalized_draft is not None
    assert finalized_draft.finalized_submission_id == submission.id
    assert finalized_draft.finalized_at is not None

    async with async_session.bind.connect() as connection:
        fresh_session = async_sessionmaker(
            bind=connection, expire_on_commit=False, autoflush=False
        )
        async with fresh_session() as check_db:
            refreshed_session = await check_db.get(
                CandidateSession, candidate_session.id
            )
            assert refreshed_session is not None
            assert refreshed_session.status == "completed"
            assert refreshed_session.completed_at is not None
