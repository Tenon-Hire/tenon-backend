"""Application module for integrations github webhooks handlers workflow run parse handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_models_handler import (
    WorkflowRunCompletedEvent,
)


def normalized_lower(value: Any) -> str | None:
    """Execute normalized lower."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def coerce_positive_int(value: Any) -> int | None:
    """Execute coerce positive int."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_github_datetime(value: Any) -> datetime | None:
    """Parse github datetime."""
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def parse_workflow_run_completed_event(
    payload: dict[str, Any],
) -> WorkflowRunCompletedEvent | None:
    """Parse workflow run completed event."""
    workflow_run = payload.get("workflow_run")
    repository = payload.get("repository")
    if not isinstance(workflow_run, dict) or not isinstance(repository, dict):
        return None
    workflow_run_id = coerce_positive_int(workflow_run.get("id"))
    repo_full_name_raw = repository.get("full_name")
    repo_full_name = (
        repo_full_name_raw.strip() if isinstance(repo_full_name_raw, str) else ""
    )
    if workflow_run_id is None or not repo_full_name:
        return None
    run_attempt = coerce_positive_int(workflow_run.get("run_attempt"))
    head_sha = workflow_run.get("head_sha")
    return WorkflowRunCompletedEvent(
        workflow_run_id=workflow_run_id,
        run_attempt=run_attempt,
        conclusion=normalized_lower(workflow_run.get("conclusion")),
        completed_at=parse_github_datetime(workflow_run.get("completed_at")),
        head_sha=head_sha.strip() if isinstance(head_sha, str) else None,
        repo_full_name=repo_full_name,
    )


__all__ = [
    "coerce_positive_int",
    "normalized_lower",
    "parse_github_datetime",
    "parse_workflow_run_completed_event",
]
