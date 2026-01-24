from __future__ import annotations

# NOTE: Exceeds 50 LOC to keep parsed-output normalization in one place without altering behavior.
from app.domains.submissions.presenter.redaction import redact_text
from app.domains.submissions.presenter.truncate import truncate_output

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


def process_parsed_output(
    parsed_output, *, include_output: bool, max_output_chars: int
):
    passed_val = failed_val = total_val = run_id = conclusion = timeout = summary = None
    stdout = stderr = None
    stdout_truncated = stderr_truncated = None
    sanitized_output = parsed_output if parsed_output else None
    artifact_error = None

    if isinstance(parsed_output, dict) and not parsed_output:
        return (None,) * 13

    if isinstance(parsed_output, dict):
        passed_val = _safe_int(parsed_output.get("passed"))
        failed_val = _safe_int(parsed_output.get("failed"))
        total_val = _safe_int(parsed_output.get("total"))
        run_id = parsed_output.get("runId") or parsed_output.get("run_id")
        conclusion_raw = parsed_output.get("conclusion")
        conclusion = conclusion or (
            str(conclusion_raw).lower() if conclusion_raw else None
        )
        timeout = timeout or (
            parsed_output.get("timeout") is True or conclusion == "timed_out"
        )
        summary_val = parsed_output.get("summary")
        summary = summary_val if isinstance(summary_val, dict) else None
        stdout_raw = parsed_output.get("stdout")
        stderr_raw = parsed_output.get("stderr")
        if isinstance(stdout_raw, str):
            stdout_clean = redact_text(stdout_raw)
            stdout, stdout_truncated = truncate_output(
                stdout_clean, max_chars=max_output_chars
            )
        if isinstance(stderr_raw, str):
            stderr_clean = redact_text(stderr_raw)
            stderr, stderr_truncated = truncate_output(
                stderr_clean, max_chars=max_output_chars
            )
        whitelisted_output = {
            key: parsed_output.get(key)
            for key in _OUTPUT_WHITELIST_KEYS
            if key in parsed_output
        }
        if stdout_raw is not None:
            whitelisted_output["stdout"] = stdout
        if stderr_raw is not None:
            whitelisted_output["stderr"] = stderr
        sanitized_output = whitelisted_output if include_output else None
        artifact_error = parsed_output.get("artifactErrorCode") or parsed_output.get(
            "artifact_error_code"
        )
        if isinstance(artifact_error, str):
            artifact_error = artifact_error.lower()
    elif isinstance(parsed_output, str):
        redacted = redact_text(parsed_output)
        text, truncated = truncate_output(redacted, max_chars=max_output_chars)
        sanitized_output = text if include_output else None
        stdout_truncated = stdout_truncated or truncated
        stderr_truncated = stderr_truncated or truncated
    return (
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
    )


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
