"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime core service workflows."""

from __future__ import annotations

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_commit_apply_service import (
    apply_bundle_commit,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_event_logs_service import (
    log_apply_attempt,
    log_apply_success,
    log_marker_found,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_lookup_service import (
    lookup_bundle_context,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_messages_service import (
    build_precommit_commit_marker,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_results_service import (
    result_already_applied,
    result_applied,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_validation_service import (
    validate_base_template_sha,
)


async def apply_precommit_bundle_if_available(
    db,
    *,
    scenario_repo_module,
    bundle_repo_module,
    github_client,
    candidate_session,
    task,
    repo_full_name: str,
    default_branch: str | None,
    base_template_sha: str | None,
    existing_precommit_sha: str | None,
    find_marker_commit_sha,
    parse_patch_entries,
    logger,
):
    """Apply precommit bundle if available."""
    early_result, context = await lookup_bundle_context(
        db,
        scenario_repo_module=scenario_repo_module,
        bundle_repo_module=bundle_repo_module,
        candidate_session=candidate_session,
        task=task,
        repo_full_name=repo_full_name,
        default_branch=default_branch,
        existing_precommit_sha=existing_precommit_sha,
    )
    if early_result is not None:
        return early_result

    marker = build_precommit_commit_marker(
        context.bundle_id, context.bundle.content_sha256
    )
    existing_marker_sha = await find_marker_commit_sha(
        github_client,
        repo_full_name=context.repo_full_name,
        branch=context.default_branch,
        marker=marker,
    )
    if existing_marker_sha:
        log_marker_found(
            logger, context=context, existing_marker_sha=existing_marker_sha
        )
        return result_already_applied(
            existing_marker_sha,
            bundle_id=context.bundle_id,
            reason="marker_commit_exists",
        )

    validate_base_template_sha(base_template_sha, context)
    changes = parse_patch_entries(
        patch_text=context.bundle.patch_text, storage_ref=context.bundle.storage_ref
    )
    if not changes:
        raise ApiError(
            status_code=500,
            detail="Precommit bundle has no file changes.",
            error_code="PRECOMMIT_BUNDLE_EMPTY",
            details={"bundleId": context.bundle_id},
        )
    log_apply_attempt(logger, context=context, file_change_count=len(changes))
    outcome = await apply_bundle_commit(
        github_client,
        context=context,
        marker=marker,
        changes=changes,
        find_marker_commit_sha=find_marker_commit_sha,
        logger=logger,
    )
    if outcome.recovered_from_conflict:
        return result_already_applied(
            outcome.commit_sha,
            bundle_id=context.bundle_id,
            reason="marker_found_after_ref_conflict",
        )
    log_apply_success(logger, context=context, commit_sha=outcome.commit_sha)
    return result_applied(outcome.commit_sha, bundle_id=context.bundle_id)
