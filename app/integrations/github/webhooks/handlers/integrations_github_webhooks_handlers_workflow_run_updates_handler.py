"""Application module for integrations github webhooks handlers workflow run updates handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_models_handler import (
    WorkflowRunCompletedEvent,
)
from app.shared.database.shared_database_models_model import Submission, Workspace


def apply_submission_completion(
    submission: Submission, *, event: WorkflowRunCompletedEvent
) -> bool:
    """Apply submission completion."""
    changed = False
    workflow_run_id = str(event.workflow_run_id)
    if submission.workflow_run_id != workflow_run_id:
        submission.workflow_run_id = workflow_run_id
        changed = True
    if submission.workflow_run_status != "completed":
        submission.workflow_run_status = "completed"
        changed = True
    if submission.workflow_run_conclusion != event.conclusion:
        submission.workflow_run_conclusion = event.conclusion
        changed = True
    if (
        event.run_attempt is not None
        and submission.workflow_run_attempt != event.run_attempt
    ):
        submission.workflow_run_attempt = event.run_attempt
        changed = True
    if event.completed_at is not None:
        if submission.workflow_run_completed_at != event.completed_at:
            submission.workflow_run_completed_at = event.completed_at
            changed = True
        if submission.last_run_at != event.completed_at:
            submission.last_run_at = event.completed_at
            changed = True
    elif submission.last_run_at is None:
        submission.last_run_at = datetime.now(UTC).replace(microsecond=0)
        changed = True
    if event.head_sha and submission.commit_sha != event.head_sha:
        submission.commit_sha = event.head_sha
        changed = True
    return changed


def apply_workspace_completion(
    workspace: Workspace, *, event: WorkflowRunCompletedEvent
) -> bool:
    """Apply workspace completion."""
    changed = False
    workflow_run_id = str(event.workflow_run_id)
    if workspace.last_workflow_run_id != workflow_run_id:
        workspace.last_workflow_run_id = workflow_run_id
        changed = True
    if workspace.last_workflow_conclusion != event.conclusion:
        workspace.last_workflow_conclusion = event.conclusion
        changed = True
    if event.head_sha and workspace.latest_commit_sha != event.head_sha:
        workspace.latest_commit_sha = event.head_sha
        changed = True
    return changed


__all__ = [
    "apply_submission_completion",
    "apply_workspace_completion",
]
