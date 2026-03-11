from __future__ import annotations

from datetime import UTC, datetime

from app.domains.submissions import service_recruiter as recruiter_sub_service
from app.domains.submissions.presenter.detail_payload import (
    build_code_payload,
    build_task_payload,
)
from app.domains.submissions.presenter.links import build_diff_url, build_links
from app.domains.submissions.presenter.output import (
    max_output_chars,
    parse_diff_summary,
)
from app.domains.submissions.presenter.test_results import build_test_results
from app.services.media.keys import recording_public_id


def _resolve_commit_basis(sub, day_audit):
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    return (
        cutoff_commit_sha or getattr(sub, "commit_sha", None),
        cutoff_commit_sha,
        cutoff_at,
        getattr(day_audit, "eval_basis_ref", None),
    )


def _build_recording_payload(recording, *, download_url: str | None):
    if recording is None:
        return None
    return {
        "recordingId": recording_public_id(recording.id),
        "contentType": recording.content_type,
        "bytes": recording.bytes,
        "status": recording.status,
        "createdAt": recording.created_at,
        "downloadUrl": download_url,
    }


def _build_transcript_payload(transcript):
    if transcript is None:
        return None
    segments = transcript.segments_json
    return {
        "status": transcript.status,
        "modelName": transcript.model_name,
        "text": transcript.text,
        "segmentsJson": segments,
        "segments": segments,
    }


def _build_handoff_payload(
    recording,
    *,
    download_url: str | None,
    transcript_payload,
):
    if recording is None:
        return None
    return {
        "recordingId": recording_public_id(recording.id),
        "downloadUrl": download_url,
        "transcript": transcript_payload,
    }


def present_detail(
    sub,
    task,
    cs,
    _sim,
    *,
    day_audit=None,
    recording=None,
    transcript=None,
    recording_download_url: str | None = None,
):
    parsed_output = recruiter_sub_service.parse_test_output(
        getattr(sub, "test_output", None)
    )
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_sha, cutoff_commit_sha, cutoff_at, eval_basis_ref = _resolve_commit_basis(
        sub, day_audit
    )
    commit_url, workflow_url = build_links(
        repo_full_name, commit_sha, sub.workflow_run_id
    )
    test_results = build_test_results(
        sub,
        parsed_output,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=True,
        max_output_chars=max_output_chars(True),
        commit_sha_override=commit_sha,
    )
    transcript_payload = _build_transcript_payload(transcript)
    return {
        "submissionId": sub.id,
        "candidateSessionId": cs.id,
        "task": build_task_payload(task),
        "contentText": sub.content_text,
        "contentJson": getattr(sub, "content_json", None),
        "code": build_code_payload(sub),
        "testResults": test_results,
        "diffSummary": diff_summary,
        "submittedAt": sub.submitted_at,
        "commitSha": commit_sha,
        "cutoffCommitSha": cutoff_commit_sha,
        "cutoffAt": cutoff_at,
        "evalBasisRef": eval_basis_ref,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "diffUrl": build_diff_url(repo_full_name, diff_summary),
        "recording": _build_recording_payload(
            recording, download_url=recording_download_url
        ),
        "transcript": transcript_payload,
        "handoff": _build_handoff_payload(
            recording,
            download_url=recording_download_url,
            transcript_payload=transcript_payload,
        ),
    }
