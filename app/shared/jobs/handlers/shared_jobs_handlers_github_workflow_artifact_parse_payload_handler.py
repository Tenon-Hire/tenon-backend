"""Application module for jobs handlers github workflow artifact parse payload handler workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ArtifactParsePayload:
    """Represent artifact parse payload data and behavior."""

    submission_id: int | None
    workflow_run_id: int | None
    workflow_run_attempt: int | None
    repo_full_name: str | None
    payload_candidate_session_id: int | None
    payload_task_id: int | None
    workflow_completed_at: datetime | None


def build_payload(
    payload_json: dict[str, Any],
    *,
    parse_positive_int: Callable[[Any], int | None],
    parse_iso_datetime: Callable[[Any], datetime | None],
    normalized_text: Callable[[Any], str | None],
) -> ArtifactParsePayload:
    """Build payload."""
    return ArtifactParsePayload(
        submission_id=parse_positive_int(payload_json.get("submissionId")),
        workflow_run_id=parse_positive_int(payload_json.get("workflowRunId")),
        workflow_run_attempt=parse_positive_int(payload_json.get("workflowRunAttempt")),
        repo_full_name=normalized_text(payload_json.get("repoFullName")),
        payload_candidate_session_id=parse_positive_int(
            payload_json.get("candidateSessionId")
        ),
        payload_task_id=parse_positive_int(payload_json.get("taskId")),
        workflow_completed_at=parse_iso_datetime(
            payload_json.get("workflowCompletedAt")
        ),
    )


def invalid_payload_response(payload: ArtifactParsePayload) -> dict[str, Any] | None:
    """Execute invalid payload response."""
    if (
        payload.submission_id is not None
        and payload.workflow_run_id is not None
        and payload.repo_full_name is not None
    ):
        return None
    return {
        "status": "skipped_invalid_payload",
        "submissionId": payload.submission_id,
        "workflowRunId": payload.workflow_run_id,
        "repoFullName": payload.repo_full_name,
    }
