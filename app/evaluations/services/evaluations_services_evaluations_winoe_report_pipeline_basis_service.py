"""Application module for evaluations services evaluations winoe report pipeline basis service workflows."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    Submission,
    Transcript,
)


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _submission_basis_hash(submission: Submission | None) -> str | None:
    if submission is None:
        return None
    submission_basis = {
        "id": submission.id,
        "submittedAt": submission.submitted_at.isoformat()
        if submission.submitted_at
        else None,
        "contentText": submission.content_text,
        "contentJson": submission.content_json,
        "commitSha": submission.commit_sha,
        "checkpointSha": submission.checkpoint_sha,
        "finalSha": submission.final_sha,
        "workflowRunId": submission.workflow_run_id,
        "diffSummaryJson": submission.diff_summary_json,
        "testsPassed": submission.tests_passed,
        "testsFailed": submission.tests_failed,
        "testOutput": submission.test_output,
        "lastRunAt": submission.last_run_at.isoformat()
        if submission.last_run_at
        else None,
    }
    return _stable_hash(submission_basis)


def _transcript_basis_hash(transcript: Transcript | None) -> str | None:
    if transcript is None:
        return None
    transcript_basis = {
        "id": transcript.id,
        "status": transcript.status,
        "modelName": transcript.model_name,
        "text": transcript.text,
        "segments": transcript.segments_json,
    }
    return _stable_hash(transcript_basis)


def _build_basis_references(
    *,
    scenario_version_id: int,
    scenario_rubric_version: str,
    day_audits: dict[int, CandidateDayAudit],
    submissions_by_day: dict[int, Submission],
    transcript_reference: str,
    transcript_hash: str | None,
    disabled_day_indexes: list[int],
) -> dict[str, Any]:
    day_refs = {
        str(day_index): {
            "submissionId": (
                submissions_by_day[day_index].id
                if day_index in submissions_by_day
                else None
            ),
            "submissionBasisHash": _submission_basis_hash(
                submissions_by_day.get(day_index)
            ),
            "cutoffCommitSha": day_audits[day_index].cutoff_commit_sha
            if day_index in day_audits
            else None,
            "evalBasisRef": day_audits[day_index].eval_basis_ref
            if day_index in day_audits
            else None,
        }
        for day_index in range(1, 6)
    }
    return {
        "scenarioVersionId": scenario_version_id,
        "rubricVersion": scenario_rubric_version,
        "dayRefs": day_refs,
        "transcriptReference": transcript_reference,
        "transcriptBasisHash": transcript_hash,
        "disabledDayIndexes": disabled_day_indexes,
    }


__all__ = [
    "_build_basis_references",
    "_stable_hash",
    "_submission_basis_hash",
    "_transcript_basis_hash",
]
