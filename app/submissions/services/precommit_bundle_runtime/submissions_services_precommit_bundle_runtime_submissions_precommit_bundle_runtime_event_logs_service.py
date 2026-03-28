"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime event logs service workflows."""

from __future__ import annotations


def log_marker_found(logger, *, context, existing_marker_sha: str) -> None:
    """Execute log marker found."""
    logger.info(
        "precommit_bundle_marker_found_existing_commit",
        extra={
            "candidateSessionId": context.candidate_session_id,
            "scenarioVersionId": context.scenario_version_id,
            "taskId": context.task_id,
            "repoFullName": context.repo_full_name,
            "templateKey": context.template_key,
            "bundleId": context.bundle_id,
            "precommitSha": existing_marker_sha,
        },
    )


def log_apply_attempt(logger, *, context, file_change_count: int) -> None:
    """Execute log apply attempt."""
    logger.info(
        "precommit_bundle_apply_attempt",
        extra={
            "candidateSessionId": context.candidate_session_id,
            "scenarioVersionId": context.scenario_version_id,
            "taskId": context.task_id,
            "repoFullName": context.repo_full_name,
            "templateKey": context.template_key,
            "bundleId": context.bundle_id,
            "branch": context.default_branch,
            "fileChangeCount": file_change_count,
        },
    )


def log_apply_success(logger, *, context, commit_sha: str) -> None:
    """Execute log apply success."""
    logger.info(
        "precommit_bundle_apply_success",
        extra={
            "candidateSessionId": context.candidate_session_id,
            "scenarioVersionId": context.scenario_version_id,
            "taskId": context.task_id,
            "repoFullName": context.repo_full_name,
            "templateKey": context.template_key,
            "bundleId": context.bundle_id,
            "precommitSha": commit_sha,
        },
    )


__all__ = ["log_apply_attempt", "log_apply_success", "log_marker_found"]
