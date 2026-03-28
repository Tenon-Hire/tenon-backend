"""Application module for submissions services submissions workspace creation strategy service workflows."""

from __future__ import annotations

import contextlib

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    WorkspaceGroup,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    resolve_workspace_key_for_task,
)


async def resolve_workspace_strategy(db, candidate_session, task, workspace_resolution):
    """Resolve workspace strategy."""
    workspace_key = resolve_workspace_key_for_task(task)
    uses_grouped_workspace = False
    existing_group: WorkspaceGroup | None = None
    checked = bool(
        workspace_resolution is not None
        and workspace_resolution.workspace_group_checked
    )
    if workspace_resolution is not None:
        workspace_key = workspace_resolution.workspace_key or workspace_key
        return (
            workspace_key,
            workspace_resolution.uses_grouped_workspace,
            workspace_resolution.workspace_group,
            checked,
        )
    if hasattr(db, "execute"):
        resolution = await workspace_repo.resolve_workspace_resolution(
            db,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            task_day_index=getattr(task, "day_index", None),
            task_type=getattr(task, "type", None),
        )
        workspace_key = resolution.workspace_key or workspace_key
        return (
            workspace_key,
            resolution.uses_grouped_workspace,
            resolution.workspace_group,
            bool(resolution.workspace_group_checked),
        )
    uses_grouped_workspace = await workspace_repo.session_uses_grouped_workspace(
        db, candidate_session_id=candidate_session.id, workspace_key=workspace_key
    )
    if uses_grouped_workspace:
        with contextlib.suppress(AttributeError):
            existing_group = await workspace_repo.get_workspace_group(
                db,
                candidate_session_id=candidate_session.id,
                workspace_key=workspace_key,
            )
    return workspace_key, uses_grouped_workspace, existing_group, False
