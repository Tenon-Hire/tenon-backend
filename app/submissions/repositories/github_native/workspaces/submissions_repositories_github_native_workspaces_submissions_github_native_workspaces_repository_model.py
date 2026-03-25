from __future__ import annotations

from dataclasses import dataclass

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    WorkspaceGroup,
)


@dataclass(slots=True)
class WorkspaceResolution:
    workspace_key: str | None
    uses_grouped_workspace: bool
    workspace_group: WorkspaceGroup | None = None
    workspace_group_checked: bool = False


__all__ = ["WorkspaceResolution"]
