from __future__ import annotations

import pytest

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
)
from tests.submissions.repositories.github_native.workspaces.submissions_github_native_workspaces_groups_test_utils import (
    create_coding_workspace_group,
    create_workspace,
    seed_candidate_workspace_session,
)


@pytest.mark.asyncio
async def test_session_uses_grouped_workspace_for_new_session(async_session):
    candidate_session, _tasks = await seed_candidate_workspace_session(
        async_session,
        email="grouped-eligible@sim.com",
    )
    uses_grouped = await workspace_repo.session_uses_grouped_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key=CODING_WORKSPACE_KEY,
    )
    assert uses_grouped is True


@pytest.mark.asyncio
async def test_session_uses_grouped_workspace_disabled_for_legacy_session(
    async_session,
):
    candidate_session, tasks = await seed_candidate_workspace_session(
        async_session,
        email="legacy-safe@sim.com",
    )
    await create_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
        repo_id=123,
    )

    uses_grouped = await workspace_repo.session_uses_grouped_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key=CODING_WORKSPACE_KEY,
    )
    assert uses_grouped is False


@pytest.mark.asyncio
async def test_session_uses_grouped_workspace_if_group_exists(async_session):
    candidate_session, tasks = await seed_candidate_workspace_session(
        async_session,
        email="group-exists@sim.com",
    )
    await create_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
        repo_id=123,
    )
    await create_coding_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        task=tasks[1],
    )

    uses_grouped = await workspace_repo.session_uses_grouped_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key=CODING_WORKSPACE_KEY,
    )
    assert uses_grouped is True
