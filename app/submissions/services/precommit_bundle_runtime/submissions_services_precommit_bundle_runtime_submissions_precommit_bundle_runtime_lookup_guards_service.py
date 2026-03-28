"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime lookup guards service workflows."""

from __future__ import annotations

from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_results_service import (
    result_already_applied,
    result_no_bundle,
)
from app.submissions.services.submissions_services_submissions_payload_validation_service import (
    CODE_TASK_TYPES,
)


def evaluate_lookup_guards(
    *,
    candidate_session_id: object,
    scenario_version_id: object,
    task_id: object,
    task_type: str,
    repo_full_name: str,
    existing_precommit_sha: str | None,
    logger,
):
    """Execute evaluate lookup guards."""
    if existing_precommit_sha:
        logger.info(
            "precommit_bundle_skipped_existing_sha",
            extra={
                "candidateSessionId": candidate_session_id,
                "scenarioVersionId": scenario_version_id,
                "taskId": task_id,
                "repoFullName": repo_full_name,
                "precommitSha": existing_precommit_sha,
            },
        )
        return result_already_applied(
            existing_precommit_sha,
            bundle_id=None,
            reason="workspace_precommit_sha_present",
        )
    if task_type not in CODE_TASK_TYPES:
        logger.info(
            "precommit_bundle_skipped_non_code_task",
            extra={
                "candidateSessionId": candidate_session_id,
                "scenarioVersionId": scenario_version_id,
                "taskId": task_id,
                "taskType": task_type,
                "repoFullName": repo_full_name,
            },
        )
        return result_no_bundle(reason="non_code_task", taskType=task_type)
    if not scenario_version_id:
        logger.info(
            "precommit_bundle_skipped_missing_scenario_version",
            extra={
                "candidateSessionId": candidate_session_id,
                "taskId": task_id,
                "repoFullName": repo_full_name,
            },
        )
        return result_no_bundle(reason="missing_scenario_version")
    return None


__all__ = ["evaluate_lookup_guards"]
