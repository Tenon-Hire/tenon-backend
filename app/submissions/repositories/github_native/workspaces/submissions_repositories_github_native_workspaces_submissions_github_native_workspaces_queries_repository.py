"""Application module for submissions repositories github native workspaces submissions github native workspaces queries repository workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)


async def get_by_session_and_workspace_key(
    db: AsyncSession, *, candidate_session_id: int, workspace_key: str
) -> Workspace | None:
    """Return by session and workspace key."""
    stmt = (
        select(Workspace)
        .join(WorkspaceGroup, Workspace.workspace_group_id == WorkspaceGroup.id)
        .where(
            Workspace.candidate_session_id == candidate_session_id,
            WorkspaceGroup.candidate_session_id == candidate_session_id,
            WorkspaceGroup.workspace_key == workspace_key,
        )
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_by_workspace_group_id(
    db: AsyncSession, *, workspace_group_id: str
) -> Workspace | None:
    """Return by workspace group id."""
    stmt = (
        select(Workspace)
        .where(Workspace.workspace_group_id == workspace_group_id)
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_workspace_group(
    db: AsyncSession, *, candidate_session_id: int, workspace_key: str
) -> WorkspaceGroup | None:
    """Return workspace group."""
    stmt = select(WorkspaceGroup).where(
        WorkspaceGroup.candidate_session_id == candidate_session_id,
        WorkspaceGroup.workspace_key == workspace_key,
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


__all__ = [
    "get_by_session_and_workspace_key",
    "get_by_workspace_group_id",
    "get_workspace_group",
]
