from __future__ import annotations


def should_skip(
    status_str,
    passed_val,
    failed_val,
    total_val,
    sanitized_output,
    workflow_run_id,
    commit_sha,
    last_run_at,
):
    if status_str is None and passed_val is None and failed_val is None and total_val is None:
        if sanitized_output is None and workflow_run_id is None and commit_sha is None and last_run_at is None:
            return True
    return False
