"""Application module for submissions repositories github native workspaces submissions github native workspaces resolution repository workflows."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import and_, exists, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_repository_model import (
    WorkspaceResolution,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
    resolve_workspace_key,
)
from app.tasks.repositories.tasks_repositories_tasks_repository_model import Task


async def _resolve_workspace_key_for_task_id(
    db: AsyncSession, *, task_id: int
) -> str | None:
    stmt = select(Task.day_index, Task.type).where(Task.id == task_id)
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None
    return resolve_workspace_key(day_index=row.day_index, task_type=row.type)


def _legacy_workspace_exists_expr(*, candidate_session_id: int, workspace_key: str):
    if workspace_key != CODING_WORKSPACE_KEY:
        return literal(False)
    return exists(
        select(literal(1))
        .select_from(Workspace)
        .join(Task, Workspace.task_id == Task.id)
        .where(
            Workspace.candidate_session_id == candidate_session_id,
            Workspace.workspace_group_id.is_(None),
            Task.day_index.in_((2, 3)),
            Task.type.in_(("code", "debug")),
        )
    )


async def _workspace_key_state(
    db: AsyncSession, *, candidate_session_id: int, workspace_key: str
) -> tuple[WorkspaceGroup | None, bool]:
    anchor = select(literal(1).label("anchor")).subquery()
    legacy_exists = _legacy_workspace_exists_expr(
        candidate_session_id=candidate_session_id,
        workspace_key=workspace_key,
    )
    stmt = (
        select(WorkspaceGroup, legacy_exists.label("has_legacy_workspace"))
        .select_from(anchor)
        .outerjoin(
            WorkspaceGroup,
            and_(
                WorkspaceGroup.candidate_session_id == candidate_session_id,
                WorkspaceGroup.workspace_key == workspace_key,
            ),
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None, False
    group, has_legacy_workspace = row
    return group, bool(has_legacy_workspace)


async def resolve_workspace_resolution_impl(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    workspace_key: str | None = None,
    task_id: int | None = None,
    task_day_index: int | None = None,
    task_type: str | None = None,
    resolve_workspace_key_for_task_id: Callable[
        ..., object
    ] = _resolve_workspace_key_for_task_id,
    workspace_key_state: Callable[..., object] = _workspace_key_state,
) -> WorkspaceResolution:
    """Resolve workspace resolution impl."""
    resolved_key = workspace_key
    if resolved_key is None:
        if task_day_index is not None and task_type is not None:
            resolved_key = resolve_workspace_key(
                day_index=task_day_index, task_type=task_type
            )
        elif task_id is not None:
            resolved_key = await resolve_workspace_key_for_task_id(db, task_id=task_id)
    if not resolved_key:
        return WorkspaceResolution(
            workspace_key=resolved_key,
            uses_grouped_workspace=False,
            workspace_group=None,
            workspace_group_checked=False,
        )
    existing_group, has_legacy_workspace = await workspace_key_state(
        db, candidate_session_id=candidate_session_id, workspace_key=resolved_key
    )
    if existing_group is not None:
        return WorkspaceResolution(
            workspace_key=resolved_key,
            uses_grouped_workspace=True,
            workspace_group=existing_group,
            workspace_group_checked=True,
        )
    return WorkspaceResolution(
        workspace_key=resolved_key,
        uses_grouped_workspace=not has_legacy_workspace,
        workspace_group=None,
        workspace_group_checked=True,
    )


__all__ = ["resolve_workspace_resolution_impl"]
