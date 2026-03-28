"""Application module for integrations github webhooks handlers workflow run models handler workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE = "github_workflow_artifact_parse"
NON_TERMINAL_WORKFLOW_STATUSES = (
    "queued",
    "in_progress",
    "requested",
    "pending",
    "waiting",
)


@dataclass(frozen=True)
class WorkflowRunCompletedEvent:
    """Represent workflow run completed event data and behavior."""

    workflow_run_id: int
    run_attempt: int | None
    conclusion: str | None
    completed_at: datetime | None
    head_sha: str | None
    repo_full_name: str


@dataclass(frozen=True)
class WorkflowRunWebhookOutcome:
    """Represent workflow run webhook outcome data and behavior."""

    outcome: str
    reason_code: str | None = None
    submission_id: int | None = None
    workflow_run_id: int | None = None
    enqueued_artifact_parse: bool = False


__all__ = [
    "GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE",
    "NON_TERMINAL_WORKFLOW_STATUSES",
    "WorkflowRunCompletedEvent",
    "WorkflowRunWebhookOutcome",
]
