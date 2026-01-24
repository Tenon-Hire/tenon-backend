from __future__ import annotations

# NOTE: Exceeds 50 LOC to keep test result assembly cohesive and avoid behavior drift.
from app.domains.submissions import service_recruiter as recruiter_sub_service
from app.domains.submissions.presenter.parsed_output import (
    _safe_int,
    process_parsed_output,
)


def build_test_results(
    sub,
    parsed_output,
    *,
    workflow_url: str | None,
    commit_url: str | None,
    include_output: bool,
    max_output_chars: int,
):
    (
        passed_val,
        failed_val,
        total_val,
        run_id,
        conclusion,
        timeout,
        summary,
        stdout,
        stderr,
        stdout_truncated,
        stderr_truncated,
        sanitized_output,
        artifact_error,
    ) = process_parsed_output(parsed_output, include_output=include_output, max_output_chars=max_output_chars)

    workflow_run_id = getattr(sub, "workflow_run_id", None)
    commit_sha = getattr(sub, "commit_sha", None)
    last_run_at = getattr(sub, "last_run_at", None)
    if total_val is None and (passed_val is not None or failed_val is not None):
        total_val = (passed_val or 0) + (failed_val or 0)

    status_str = recruiter_sub_service.derive_test_status(passed_val, failed_val, parsed_output)
    if run_id is None and workflow_run_id:
        run_id = _safe_int(workflow_run_id) or workflow_run_id

    db_status = getattr(sub, "workflow_run_status", None)
    if isinstance(db_status, str):
        run_status = db_status.lower()
    else:
        run_status = None
    db_conclusion = getattr(sub, "workflow_run_conclusion", None)
    if isinstance(db_conclusion, str):
        conclusion = db_conclusion.lower()
    if timeout is None and conclusion == "timed_out":
        timeout = True
    workflow_run_id_str = str(workflow_run_id) if workflow_run_id is not None else None

    artifact_present = parsed_output is not None or any(v is not None for v in (passed_val, failed_val, total_val))
    if status_str is None and passed_val is None and failed_val is None and total_val is None and sanitized_output is None and workflow_run_id is None and commit_sha is None and last_run_at is None:
        return None

    result = {
        "status": status_str,
        "passed": passed_val,
        "failed": failed_val,
        "total": total_val,
        "runId": run_id,
        "runStatus": run_status,
        "conclusion": conclusion,
        "timeout": timeout,
        "stdout": stdout,
        "stderr": stderr,
        "stdoutTruncated": stdout_truncated,
        "stderrTruncated": stderr_truncated,
        "summary": summary,
        "lastRunAt": last_run_at,
        "workflowRunId": workflow_run_id_str,
        "commitSha": commit_sha,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "artifactName": "tenon-test-results" if artifact_present else None,
        "artifactPresent": True if artifact_present else None,
        "artifactErrorCode": artifact_error,
    }
    if include_output:
        result["output"] = sanitized_output
    return result
