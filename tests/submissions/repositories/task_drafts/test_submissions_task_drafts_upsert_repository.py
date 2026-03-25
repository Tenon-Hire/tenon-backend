from __future__ import annotations

import pytest

from app.submissions.repositories.task_drafts import repository as task_drafts_repo
from tests.submissions.repositories.task_drafts.test_submissions_task_drafts_repository_utils import (
    seed_context,
)


@pytest.mark.asyncio
async def test_upsert_create_fetch_and_update(async_session):
    candidate_session, task = await seed_context(async_session)
    created = await task_drafts_repo.upsert_draft(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        content_text="initial",
        content_json={"a": 1},
    )
    assert created.id is not None and created.content_text == "initial"
    assert created.content_json == {"a": 1}

    fetched = await task_drafts_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert fetched is not None and fetched.id == created.id

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
    assert refreshed is not None and refreshed.content_text == "updated"
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
    candidate_session, task = await seed_context(async_session)
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
