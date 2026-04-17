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
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)


async def fetch_workspace_and_branch(
    db: AsyncSession,
    candidate_session,
    task,
    payload,
) -> tuple[Workspace, str]:
    # Favor a direct task-scoped lookup first. This avoids extra resolution
    # queries on the submit hot path while preserving grouped fallback behavior.
    """Return workspace and branch."""
    workspace = await submission_service.workspace_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        workspace_resolution=WorkspaceResolution(
            workspace_key=None,
            uses_grouped_workspace=False,
        ),
    )
    if (
        workspace is None
        and getattr(task, "day_index", None) is not None
        and getattr(task, "type", None) is not None
    ):
        workspace_key = resolve_workspace_key(
            day_index=getattr(task, "day_index", None),
            task_type=getattr(task, "type", None),
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
                    candidate_session_id=candidate_session.id,
                    workspace_key=workspace_key,
                )
    if workspace is None:
        workspace = await submission_service.workspace_repo.get_by_session_and_task(
            db,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
        )
    if workspace is None:  # pragma: no cover - defensive guard
        raise WorkspaceMissing()
    await ensure_day_flow_open(
        db,
        candidate_session=candidate_session,
        task=task,
        workspace=workspace,
    )
    branch = submission_service.validate_branch(
        getattr(payload, "branch", None) or workspace.default_branch or "main"
    )
    return workspace, branch
