from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from sqlalchemy import select

from app.integrations.github.webhooks.handlers import workflow_run
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_model import (
    Workspace,
)
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _workflow_payload(
    *,
    run_id: int,
    repo_full_name: str,
    head_sha: str | None = "sha-head",
    run_attempt: int | None = 1,
    conclusion: object = "success",
    completed_at: str | None = "2026-03-13T12:00:00Z",
) -> dict[str, object]:
    workflow_run_payload: dict[str, object] = {"id": run_id}
    if run_attempt is not None:
        workflow_run_payload["run_attempt"] = run_attempt
    if head_sha is not None:
        workflow_run_payload["head_sha"] = head_sha
    if completed_at is not None:
        workflow_run_payload["completed_at"] = completed_at
    workflow_run_payload["conclusion"] = conclusion

    return {
        "action": "completed",
        "repository": {"full_name": repo_full_name},
        "workflow_run": workflow_run_payload,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
