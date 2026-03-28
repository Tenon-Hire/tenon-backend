"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime lookup service workflows."""

from __future__ import annotations

import logging

from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_core_model import (
    DEFAULT_PRECOMMIT_BRANCH,
    BundleLookupContext,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_lookup_guards_service import (
    evaluate_lookup_guards,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_results_service import (
    result_no_bundle,
)

logger = logging.getLogger(__name__)


def _obj_id(value: object, field_name: str) -> object:
    return getattr(value, field_name, None)


def _task_type(task: object) -> str:
    return (getattr(task, "type", "") or "").strip().lower()


async def lookup_bundle_context(
    db,
    *,
    scenario_repo_module,
    bundle_repo_module,
    candidate_session,
    task,
    repo_full_name: str,
    default_branch: str | None,
    existing_precommit_sha: str | None,
):
    """Look up bundle context."""
    candidate_session_id = _obj_id(candidate_session, "id")
    scenario_version_id = _obj_id(candidate_session, "scenario_version_id")
    task_id = _obj_id(task, "id")
    task_type = _task_type(task)
    early_result = evaluate_lookup_guards(
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        task_id=task_id,
        task_type=task_type,
        repo_full_name=repo_full_name,
        existing_precommit_sha=existing_precommit_sha,
        logger=logger,
    )
    if early_result is not None:
        return early_result, None

    scenario_version = await scenario_repo_module.get_by_id(db, scenario_version_id)
    template_key = (getattr(scenario_version, "template_key", "") or "").strip()
    if not template_key:
        logger.warning(
            "precommit_bundle_lookup_missing_template_key",
            extra={
                "candidateSessionId": candidate_session_id,
                "scenarioVersionId": scenario_version_id,
                "taskId": task_id,
                "repoFullName": repo_full_name,
            },
        )
        return result_no_bundle(
            reason="missing_template_key", scenarioVersionId=scenario_version_id
        ), None

    bundle = await bundle_repo_module.get_ready_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version_id,
        template_key=template_key,
    )
    logger.info(
        "precommit_bundle_lookup_result",
        extra={
            "candidateSessionId": candidate_session_id,
            "scenarioVersionId": scenario_version_id,
            "taskId": task_id,
            "repoFullName": repo_full_name,
            "templateKey": template_key,
            "bundleFound": bundle is not None,
        },
    )
    if bundle is None:
        return result_no_bundle(
            reason="bundle_not_found",
            scenarioVersionId=scenario_version_id,
            templateKey=template_key,
        ), None

    return None, BundleLookupContext(
        candidate_session_id=candidate_session_id,
        scenario_version_id=scenario_version_id,
        task_id=task_id,
        task_type=task_type,
        repo_full_name=repo_full_name,
        default_branch=default_branch or DEFAULT_PRECOMMIT_BRANCH,
        template_key=template_key,
        bundle=bundle,
        bundle_id=int(bundle.id),
    )
