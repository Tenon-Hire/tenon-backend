from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
)
from tests.submissions.repositories.github_native.workspaces.submissions_github_native_workspaces_groups_test_utils import (
    create_coding_workspace_group,
    create_workspace,
    seed_candidate_workspace_session,
)


@pytest.mark.asyncio
async def test_workspace_group_unique_constraint(async_session):
    candidate_session, tasks = await seed_candidate_workspace_session(
        async_session,
        email="group-unique@sim.com",
    )
    first = await create_coding_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
    )
    assert first.workspace_key == CODING_WORKSPACE_KEY

    with pytest.raises(IntegrityError):
        await create_coding_workspace_group(
            async_session,
            candidate_session_id=candidate_session.id,
            task=tasks[2],
        )
    await async_session.rollback()


@pytest.mark.asyncio
async def test_workspace_group_row_unique_constraint(async_session):
    candidate_session, tasks = await seed_candidate_workspace_session(
        async_session,
        email="group-row-unique@sim.com",
    )
    group = await create_coding_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
    )
    await create_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
        repo_id=123,
        group=group,
    )

    with pytest.raises(IntegrityError):
        await create_workspace(
            async_session,
            candidate_session_id=candidate_session.id,
            task=tasks[2],
            repo_id=456,
            group=group,
        )
    await async_session.rollback()
