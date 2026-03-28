"""Application module for integrations github webhooks handlers workflow run handler workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_jobs_handler import (
    build_artifact_parse_job_idempotency_key,
    enqueue_artifact_parse_job,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_mapping_handler import (
    company_id_for_submission as _company_id_for_submission,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_mapping_handler import (
    resolve_submission_mapping as _resolve_submission_mapping,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_mapping_handler import (
    workspace_for_submission as _workspace_for_submission,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_models_handler import (
    GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
    WorkflowRunCompletedEvent,
    WorkflowRunWebhookOutcome,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_parse_handler import (
    coerce_positive_int,
    normalized_lower,
    parse_github_datetime,
    parse_workflow_run_completed_event,
)
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_updates_handler import (
    apply_submission_completion,
    apply_workspace_completion,
)

_coerce_positive_int = coerce_positive_int
_normalized_lower = normalized_lower
_parse_github_datetime = parse_github_datetime


async def process_workflow_run_completed_event(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    delivery_id: str | None,
) -> WorkflowRunWebhookOutcome:
    """Process workflow run completed event."""
    event = parse_workflow_run_completed_event(payload)
    if event is None:
        return WorkflowRunWebhookOutcome(
            outcome="ignored", reason_code="workflow_run_payload_invalid"
        )
    submission, mapping_reason = await _resolve_submission_mapping(db, event=event)
    if submission is None:
        return WorkflowRunWebhookOutcome(
            outcome="unmatched",
            reason_code=mapping_reason,
            workflow_run_id=event.workflow_run_id,
        )
    company_id = await _company_id_for_submission(db, submission=submission)
    if company_id is None:
        return WorkflowRunWebhookOutcome(
            outcome="unmatched",
            reason_code="submission_company_unresolved",
            submission_id=submission.id,
            workflow_run_id=event.workflow_run_id,
        )
    updated_submission = apply_submission_completion(submission, event=event)
    workspace = await _workspace_for_submission(db, submission=submission)
    updated_workspace = (
        apply_workspace_completion(workspace, event=event)
        if workspace is not None
        else False
    )
    enqueued_artifact_parse = await enqueue_artifact_parse_job(
        db,
        submission=submission,
        company_id=company_id,
        event=event,
        delivery_id=delivery_id,
    )
    await db.commit()
    return WorkflowRunWebhookOutcome(
        outcome="updated_status"
        if (updated_submission or updated_workspace)
        else "duplicate_noop",
        reason_code=mapping_reason,
        submission_id=submission.id,
        workflow_run_id=event.workflow_run_id,
        enqueued_artifact_parse=enqueued_artifact_parse,
    )


__all__ = [
    "GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE",
    "WorkflowRunCompletedEvent",
    "WorkflowRunWebhookOutcome",
    "_coerce_positive_int",
    "_normalized_lower",
    "_parse_github_datetime",
    "build_artifact_parse_job_idempotency_key",
    "parse_workflow_run_completed_event",
    "process_workflow_run_completed_event",
]
