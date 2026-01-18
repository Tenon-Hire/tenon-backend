"""Helpers to render recruiter-facing submission output.

This module is longer than 50 LOC to keep redaction, truncation, and link/test formatting together.
"""

from __future__ import annotations

import json
import re

from app.domains.submissions import service_recruiter as recruiter_sub_service

_MAX_OUTPUT_CHARS_LIST = 4000
_MAX_OUTPUT_CHARS_DETAIL = 20000

_TOKEN_REDACT_PATTERNS = [
    re.compile(r"gh[pous]_[A-Za-z0-9]{10,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{10,}", re.IGNORECASE),
    re.compile(r"(Authorization:\s*Bearer)\s+[^\s]+", re.IGNORECASE),
    re.compile(r"(token)\s+[A-Za-z0-9_\-]{10,}", re.IGNORECASE),
]
_OUTPUT_WHITELIST_KEYS = {
    "passed",
    "failed",
    "total",
    "stdout",
    "stderr",
    "summary",
    "runId",
    "run_id",
    "conclusion",
    "timeout",
}


def redact_text(text: str | None) -> str | None:
    if text is None:
        return None
    redacted = text
    for pattern in _TOKEN_REDACT_PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(lambda match: f"{match.group(1)} [redacted]", redacted)
        else:
            redacted = pattern.sub("[redacted]", redacted)
    return redacted


def truncate_output(text: str | None, *, max_chars: int) -> tuple[str | None, bool | None]:
    if text is None:
        return None, None
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "... (truncated)", True


def parse_diff_summary(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def build_links(repo_full_name: str | None, commit_sha: str | None, workflow_run_id):
    commit_url = f"https://github.com/{repo_full_name}/commit/{commit_sha}" if repo_full_name and commit_sha else None
    workflow_url = (
        f"https://github.com/{repo_full_name}/actions/runs/{workflow_run_id}"
        if repo_full_name and workflow_run_id
        else None
    )
    return commit_url, workflow_url


def build_diff_url(repo_full_name: str | None, diff_summary):
    if not repo_full_name or not isinstance(diff_summary, dict):
        return None
    base = diff_summary.get("base")
    head = diff_summary.get("head")
    if base and head:
        return f"https://github.com/{repo_full_name}/compare/{base}...{head}"
    return None


def build_test_results(
    sub,
    parsed_output,
    *,
    workflow_url: str | None,
    commit_url: str | None,
    include_output: bool,
    max_output_chars: int,
):
    passed_val = _safe_int(getattr(sub, "tests_passed", None))
    failed_val = _safe_int(getattr(sub, "tests_failed", None))
    workflow_run_id = getattr(sub, "workflow_run_id", None)
    commit_sha = getattr(sub, "commit_sha", None)
    last_run_at = getattr(sub, "last_run_at", None)
    total_val = run_id = run_status = conclusion = timeout = summary = None
    stdout = stderr = None
    stdout_truncated = stderr_truncated = None
    sanitized_output = parsed_output if parsed_output else None

    if isinstance(parsed_output, dict):
        if passed_val is None:
            passed_val = _safe_int(parsed_output.get("passed"))
        if failed_val is None:
            failed_val = _safe_int(parsed_output.get("failed"))
        total_val = _safe_int(parsed_output.get("total"))
        run_id = parsed_output.get("runId") or parsed_output.get("run_id")
        conclusion_raw = parsed_output.get("conclusion")
        conclusion = conclusion or (str(conclusion_raw).lower() if conclusion_raw else None)
        timeout = timeout or (parsed_output.get("timeout") is True or conclusion == "timed_out")
        summary_val = parsed_output.get("summary")
        summary = summary_val if isinstance(summary_val, dict) else None

        stdout_raw = parsed_output.get("stdout")
        stderr_raw = parsed_output.get("stderr")
        if isinstance(stdout_raw, str):
            stdout_clean = redact_text(stdout_raw)
            stdout, stdout_truncated = truncate_output(stdout_clean, max_chars=max_output_chars)
        if isinstance(stderr_raw, str):
            stderr_clean = redact_text(stderr_raw)
            stderr, stderr_truncated = truncate_output(stderr_clean, max_chars=max_output_chars)

        whitelisted_output = {}
        for key in _OUTPUT_WHITELIST_KEYS:
            if key in parsed_output:
                whitelisted_output[key] = parsed_output.get(key)
        if stdout_raw is not None:
            whitelisted_output["stdout"] = stdout
        if stderr_raw is not None:
            whitelisted_output["stderr"] = stderr
        sanitized_output = whitelisted_output if include_output else None
    elif isinstance(parsed_output, str):
        redacted = redact_text(parsed_output)
        text, truncated = truncate_output(redacted, max_chars=max_output_chars)
        sanitized_output = text if include_output else None
        stdout_truncated = stdout_truncated or truncated
        stderr_truncated = stderr_truncated or truncated

    if total_val is None and (passed_val is not None or failed_val is not None):
        total_val = (passed_val or 0) + (failed_val or 0)

    status_str = recruiter_sub_service.derive_test_status(passed_val, failed_val, parsed_output)
    if run_id is None and workflow_run_id:
        run_id = _safe_int(workflow_run_id) or workflow_run_id

    db_status = getattr(sub, "workflow_run_status", None)
    if isinstance(db_status, str):
        run_status = db_status.lower()
    db_conclusion = getattr(sub, "workflow_run_conclusion", None)
    if isinstance(db_conclusion, str):
        conclusion = db_conclusion.lower()
    if timeout is None and conclusion == "timed_out":
        timeout = True
    workflow_run_id_str = str(workflow_run_id) if workflow_run_id is not None else None

    artifact_present = parsed_output is not None or any(v is not None for v in (passed_val, failed_val, total_val))
    artifact_error = None
    if isinstance(parsed_output, dict):
        artifact_error = parsed_output.get("artifactErrorCode") or parsed_output.get("artifact_error_code")
        if isinstance(artifact_error, str):
            artifact_error = artifact_error.lower()

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


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def max_output_chars(include_output: bool) -> int:
    return _MAX_OUTPUT_CHARS_DETAIL if include_output else _MAX_OUTPUT_CHARS_LIST


def present_list_item(sub, task):
    parsed_output = recruiter_sub_service.parse_test_output(getattr(sub, "test_output", None))
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_url, workflow_url = build_links(repo_full_name, sub.commit_sha, sub.workflow_run_id)
    diff_url = build_diff_url(repo_full_name, diff_summary)
    test_results = build_test_results(
        sub,
        parsed_output,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=False,
        max_output_chars=max_output_chars(False),
    )
    return {
        "submissionId": sub.id,
        "candidateSessionId": sub.candidate_session_id,
        "taskId": sub.task_id,
        "dayIndex": task.day_index,
        "type": task.type,
        "submittedAt": sub.submitted_at,
        "repoFullName": repo_full_name,
        "repoUrl": f"https://github.com/{repo_full_name}" if repo_full_name else None,
        "workflowRunId": sub.workflow_run_id,
        "commitSha": sub.commit_sha,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "diffUrl": diff_url,
        "diffSummary": diff_summary,
        "testResults": test_results,
    }


def present_detail(sub, task, cs, sim):
    parsed_output = recruiter_sub_service.parse_test_output(getattr(sub, "test_output", None))
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_url, workflow_url = build_links(repo_full_name, sub.commit_sha, sub.workflow_run_id)
    diff_url = build_diff_url(repo_full_name, diff_summary)
    test_results = build_test_results(
        sub,
        parsed_output,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=True,
        max_output_chars=max_output_chars(True),
    )
    return {
        "submissionId": sub.id,
        "candidateSessionId": cs.id,
        "task": {
            "taskId": task.id,
            "dayIndex": task.day_index,
            "type": task.type,
            "title": getattr(task, "title", None),
            "prompt": getattr(task, "prompt", None),
        },
        "contentText": sub.content_text,
        "code": (
            {
                "repoPath": sub.code_repo_path,
                "repoFullName": sub.code_repo_path,
                "repoUrl": f"https://github.com/{sub.code_repo_path}" if sub.code_repo_path else None,
            }
            if sub.code_repo_path is not None
            else None
        ),
        "testResults": test_results,
        "diffSummary": diff_summary,
        "submittedAt": sub.submitted_at,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "diffUrl": diff_url,
    }
