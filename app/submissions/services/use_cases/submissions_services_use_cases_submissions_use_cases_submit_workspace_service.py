"""Application module for submissions services use cases submissions use cases submit workspace service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    WorkspaceMissing,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_repository import (
    WorkspaceResolution,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    resolve_workspace_key,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)


async def fetch_workspace_and_branch(
    db: AsyncSession,
    candidate_session_id: int,
    task_id: int,
    payload,
    *,
    task_day_index: int | None = None,
    task_type: str | None = None,
) -> tuple[Workspace, str]:
    # Favor a direct task-scoped lookup first. This avoids extra resolution
    # queries on the submit hot path while preserving grouped fallback behavior.
    """Return workspace and branch."""
    workspace = await submission_service.workspace_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        workspace_resolution=WorkspaceResolution(
            workspace_key=None,
            uses_grouped_workspace=False,
        ),
    )
    if workspace is None and task_day_index is not None and task_type is not None:
        workspace_key = resolve_workspace_key(
            day_index=task_day_index,
            task_type=task_type,
        )
        if workspace_key:
            lookup_by_key = getattr(
                submission_service.workspace_repo,
                "get_by_session_and_workspace_key",
                None,
            )
            if callable(lookup_by_key):
                workspace = await lookup_by_key(
                    db,
                    candidate_session_id=candidate_session_id,
                    workspace_key=workspace_key,
                )
    if workspace is None:
        workspace = await submission_service.workspace_repo.get_by_session_and_task(
            db,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
        )
    if workspace is None:  # pragma: no cover - defensive guard
        raise WorkspaceMissing()
    branch = submission_service.validate_branch(
        getattr(payload, "branch", None) or workspace.default_branch or "main"
    )
    return workspace, branch
