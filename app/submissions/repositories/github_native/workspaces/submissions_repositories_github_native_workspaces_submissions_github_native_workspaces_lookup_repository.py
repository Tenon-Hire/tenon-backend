"""Application module for submissions repositories github native workspaces submissions github native workspaces lookup repository workflows."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_repository_model import (
    WorkspaceResolution,
)


async def get_by_session_and_task_impl(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
    task_day_index: int | None = None,
    task_type: str | None = None,
    workspace_resolution: WorkspaceResolution | None = None,
    resolve_workspace_resolution: Callable[..., object],
    get_by_workspace_group_id: Callable[..., object],
    get_by_session_and_workspace_key: Callable[..., object],
) -> Workspace | None:
    """Return by session and task impl."""
    resolution = workspace_resolution or await resolve_workspace_resolution(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        task_day_index=task_day_index,
        task_type=task_type,
    )
    if resolution.uses_grouped_workspace:
        if resolution.workspace_group is not None:
            grouped = await get_by_workspace_group_id(
                db, workspace_group_id=resolution.workspace_group.id
            )
            if grouped is not None:
                return grouped
        elif resolution.workspace_key and not (
            resolution.workspace_group_checked and resolution.workspace_group is None
        ):
            grouped = await get_by_session_and_workspace_key(
                db,
                candidate_session_id=candidate_session_id,
                workspace_key=resolution.workspace_key,
            )
            if grouped is not None:
                return grouped
        return None
    stmt = select(Workspace).where(
        Workspace.candidate_session_id == candidate_session_id,
        Workspace.task_id == task_id,
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


__all__ = ["get_by_session_and_task_impl"]
