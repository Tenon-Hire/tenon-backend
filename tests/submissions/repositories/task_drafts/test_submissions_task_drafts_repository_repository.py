from __future__ import annotations

import pytest

from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from tests.shared.factories import create_submission
from tests.submissions.repositories.task_drafts.test_submissions_task_drafts_repository_utils import (
    seed_context,
)


@pytest.mark.asyncio
async def test_upsert_finalized_raises(async_session):
    candidate_session, task = await seed_context(async_session)

    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="before finalize",
        content_json={"v": 1},
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="submitted",
    )
    await async_session.commit()

    await task_drafts_repo.mark_finalized(
        async_session,
        draft=draft,
        finalized_submission_id=submission.id,
    )

    with pytest.raises(task_drafts_repo.TaskDraftFinalizedError):
        await task_drafts_repo.upsert_draft(
            async_session,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            content_text="after finalize",
            content_json={"v": 2},
        )


@pytest.mark.asyncio
async def test_mark_finalized_commit_false_and_idempotent(async_session):
    candidate_session, task = await seed_context(async_session)

    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="draft",
        content_json={"x": True},
    )
    first_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="first",
    )
    await async_session.commit()

    finalized = await task_drafts_repo.mark_finalized(
        async_session,
        draft=draft,
        finalized_submission_id=first_submission.id,
        commit=False,
    )
    await async_session.commit()

    assert finalized.finalized_submission_id == first_submission.id
    assert finalized.finalized_at is not None

    again = await task_drafts_repo.mark_finalized(
        async_session,
        draft=finalized,
        finalized_submission_id=first_submission.id + 999,
        commit=False,
    )
    assert again.finalized_submission_id == first_submission.id
