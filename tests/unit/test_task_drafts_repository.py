from __future__ import annotations

import pytest

from app.repositories.task_drafts import repository as task_drafts_repo
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


async def _seed_context(async_session):
    recruiter = await create_recruiter(async_session, email="task-draft-repo@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    return candidate_session, tasks[0]


@pytest.mark.asyncio
async def test_upsert_create_fetch_and_update(async_session):
    candidate_session, task = await _seed_context(async_session)

    created = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="initial",
        content_json={"a": 1},
    )
    assert created.id is not None
    assert created.content_text == "initial"
    assert created.content_json == {"a": 1}

    fetched = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert fetched is not None
    assert fetched.id == created.id

    updated = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="updated",
        content_json={"b": 2},
        commit=False,
    )
    await async_session.commit()

    assert updated.id == created.id
    refreshed = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert refreshed is not None
    assert refreshed.content_text == "updated"
    assert refreshed.content_json == {"b": 2}

    updated_again = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="updated again",
        content_json={"c": 3},
    )
    assert updated_again.id == created.id
    assert updated_again.content_text == "updated again"
    assert updated_again.content_json == {"c": 3}


@pytest.mark.asyncio
async def test_upsert_create_commit_false(async_session):
    candidate_session, task = await _seed_context(async_session)
    draft = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="pending",
        content_json={"pending": True},
        commit=False,
    )
    await async_session.commit()
    assert draft.id is not None
    assert draft.content_text == "pending"


@pytest.mark.asyncio
async def test_upsert_finalized_raises(async_session):
    candidate_session, task = await _seed_context(async_session)

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
    candidate_session, task = await _seed_context(async_session)

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
