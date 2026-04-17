"""Application module for submissions services use cases submissions use cases codespace status service workflows."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    WorkspaceMissing,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.submissions_services_submissions_codespace_urls_service import (
    ensure_canonical_workspace_url,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    refresh_codespace_state,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)


async def codespace_status(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    github_client: GithubClient | None = None,
):
    """Return Codespace/workflow status for a candidate task."""
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    cs_service.require_active_window(candidate_session, task)

    workspace = await submission_service.workspace_repo.get_by_session_and_task(
        db, candidate_session_id=candidate_session.id, task_id=task.id
    )
    if workspace is None:
        raise WorkspaceMissing(detail="Workspace not initialized", status_code=404)
    await ensure_day_flow_open(
        db, candidate_session=candidate_session, task=task, workspace=workspace
    )
    if github_client is not None:
        workspace = await refresh_codespace_state(
            db,
            workspace=workspace,
            github_client=github_client,
        )
    last_test_summary = None
    if workspace.last_test_summary_json:
        try:
            last_test_summary = json.loads(workspace.last_test_summary_json)
        except ValueError:
            last_test_summary = None
    if not workspace.repo_full_name:
        raise WorkspaceMissing(status_code=409)
    codespace_url = await ensure_canonical_workspace_url(db, workspace)
    return workspace, last_test_summary, codespace_url, task
