"""Application module for submissions repositories github native workspaces submissions github native workspaces core repository workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_lookup_repository import (
    get_by_session_and_task_impl,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_mutations_repository import (
    create_workspace,
    create_workspace_group,
    set_precommit_details,
    set_precommit_sha,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_queries_repository import (
    get_by_session_and_workspace_key,
    get_by_workspace_group_id,
    get_workspace_group,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_repository_model import (
    WorkspaceResolution,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_resolution_repository import (
    resolve_workspace_resolution_impl,
)


async def get_by_session_and_task(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    task_day_index: int | None = None,
    task_type: str | None = None,
    workspace_resolution: WorkspaceResolution | None = None,
) -> Workspace | None:
    """Return by session and task."""
    return await get_by_session_and_task_impl(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        task_day_index=task_day_index,
        task_type=task_type,
        workspace_resolution=workspace_resolution,
        resolve_workspace_resolution=resolve_workspace_resolution,
        get_by_workspace_group_id=get_by_workspace_group_id,
        get_by_session_and_workspace_key=get_by_session_and_workspace_key,
    )


async def resolve_workspace_resolution(
    db: AsyncSession, **kwargs
) -> WorkspaceResolution:
    """Resolve workspace resolution."""
    return await resolve_workspace_resolution_impl(db, **kwargs)


async def session_uses_grouped_workspace(
    db: AsyncSession, *, candidate_session_id: int, workspace_key: str | None
) -> bool:
    """Execute session uses grouped workspace."""
    resolution = await resolve_workspace_resolution(
        db,
        candidate_session_id=candidate_session_id,
        workspace_key=workspace_key,
    )
    return resolution.uses_grouped_workspace


__all__ = [
    "WorkspaceResolution",
    "create_workspace",
    "create_workspace_group",
    "get_by_session_and_task",
    "get_by_session_and_workspace_key",
    "get_by_workspace_group_id",
    "get_workspace_group",
    "resolve_workspace_resolution",
    "session_uses_grouped_workspace",
    "set_precommit_details",
    "set_precommit_sha",
]
