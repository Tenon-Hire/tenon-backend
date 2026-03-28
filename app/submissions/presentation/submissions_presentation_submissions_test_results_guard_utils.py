"""Application module for submissions presentation submissions test results guard utils workflows."""

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
    """Return whether skip."""
    fields = (
        status_str,
        passed_val,
        failed_val,
        total_val,
        sanitized_output,
        workflow_run_id,
        commit_sha,
        last_run_at,
    )
    return all(value is None for value in fields)
