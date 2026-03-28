"""Application module for submissions services submissions workspace records service workflows."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.actions_runner import ActionsRunResult
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)


async def record_run_result(
    db: AsyncSession, workspace: Workspace, result: ActionsRunResult
) -> Workspace:
    """Persist latest workflow result on the workspace."""
    workspace.last_workflow_run_id = str(result.run_id)
    workspace.last_workflow_conclusion = result.conclusion
    workspace.latest_commit_sha = result.head_sha
    workspace.last_test_summary_json = json.dumps(
        result.as_test_output, ensure_ascii=False
    )
    await db.commit()
    await db.refresh(workspace)
    return workspace


def build_codespace_url(repo_full_name: str) -> str:
    """Return a Codespaces deep link to resume or create a workspace."""
    return f"https://codespaces.new/{repo_full_name}?quickstart=1"
