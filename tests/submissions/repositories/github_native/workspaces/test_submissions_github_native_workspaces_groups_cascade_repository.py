from __future__ import annotations

import pytest
from sqlalchemy import select

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)
from tests.submissions.repositories.github_native.workspaces.submissions_github_native_workspaces_groups_test_utils import (
    create_coding_workspace_group,
    create_workspace,
    seed_candidate_workspace_session,
)


@pytest.mark.asyncio
async def test_candidate_session_delete_cascades_workspace_group_and_workspace(
    async_session,
):
    candidate_session, tasks = await seed_candidate_workspace_session(
        async_session,
        email="group-cascade@sim.com",
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

    await async_session.delete(candidate_session)
    await async_session.commit()

    remaining_group = (
        await async_session.execute(
            select(WorkspaceGroup).where(
                WorkspaceGroup.candidate_session_id == candidate_session.id
            )
        )
    ).scalar_one_or_none()
    remaining_workspace = (
        (
            await async_session.execute(
                select(Workspace).where(
                    Workspace.candidate_session_id == candidate_session.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert remaining_group is None
    assert remaining_workspace == []
