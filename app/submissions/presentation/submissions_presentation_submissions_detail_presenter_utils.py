"""Application module for submissions presentation submissions detail presenter utils workflows."""

from __future__ import annotations

from app.submissions.presentation.submissions_presentation_submissions_commit_basis_utils import (
    resolve_commit_basis,
)
from app.submissions.presentation.submissions_presentation_submissions_detail_media_payloads_utils import (
    build_handoff_payload,
    build_recording_payload,
    build_transcript_payload,
)
from app.submissions.presentation.submissions_presentation_submissions_detail_payload_utils import (
    build_code_payload,
    build_task_payload,
)
from app.submissions.presentation.submissions_presentation_submissions_links_utils import (
    build_diff_url,
    build_links,
)
from app.submissions.presentation.submissions_presentation_submissions_output_utils import (
    max_output_chars,
    parse_diff_summary,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_utils import (
    build_test_results,
)
from app.submissions.services import service_recruiter as recruiter_sub_service


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
    """Present detail."""
    parsed_output = recruiter_sub_service.parse_test_output(
        getattr(sub, "test_output", None)
    )
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_sha, cutoff_commit_sha, cutoff_at, eval_basis_ref = resolve_commit_basis(
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
    transcript_payload = build_transcript_payload(transcript)
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
        "recording": build_recording_payload(
            recording, download_url=recording_download_url
        ),
        "transcript": transcript_payload,
        "handoff": build_handoff_payload(
            recording,
            download_url=recording_download_url,
            transcript_payload=transcript_payload,
        ),
    }
