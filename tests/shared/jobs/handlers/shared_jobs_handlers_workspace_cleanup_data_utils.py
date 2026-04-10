from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


async def _prepare_workspace(
    async_session: AsyncSession,
    *,
    created_at: datetime,
    completed_at: datetime | None = None,
    session_status: str = "completed",
    with_cutoff: bool = False,
    github_username: str | None = "octocat",
    use_group: bool = False,
) -> tuple[int, int, str, str | None]:
    talent_partner = await create_talent_partner(
        async_session,
        email=f"workspace-cleanup-handler-{uuid4().hex}@test.com",
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status=session_status,
        with_default_schedule=True,
        completed_at=completed_at,
    )
    candidate_session.github_username = github_username
    day2_task = next(task for task in tasks if task.day_index == 2)
    workspace_group_id: str | None = None
    if use_group:
        group = await workspace_repo.create_workspace_group(
            async_session,
            candidate_session_id=candidate_session.id,
            workspace_key="coding",
            template_repo_full_name="org/template-repo",
            repo_full_name="org/candidate-repo",
            default_branch="main",
            base_template_sha="base-sha",
            created_at=created_at,
        )
        workspace_group_id = group.id
    workspace = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=workspace_group_id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/candidate-repo",
        repo_id=1234,
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    if with_cutoff:
        await cs_repo.create_day_audit_once(
            async_session,
            candidate_session_id=candidate_session.id,
            day_index=2,
            cutoff_at=created_at,
            cutoff_commit_sha="cutoff-sha",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=True,
        )
    await async_session.commit()
    return trial.company_id, candidate_session.id, workspace.id, workspace_group_id


async def _load_cleanup_record(
    async_session: AsyncSession,
    *,
    workspace_id: str,
    workspace_group_id: str | None,
):
    if workspace_group_id is not None:
        return (
            await async_session.execute(
                select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
            )
        ).scalar_one()
    return (
        await async_session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
    ).scalar_one()


__all__ = [name for name in globals() if not name.startswith("__")]
