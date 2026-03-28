"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime commit apply service workflows."""

from __future__ import annotations

from dataclasses import dataclass

from app.integrations.github.client import GithubError
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_git_tree_service import (
    build_tree_entries,
    resolve_head_and_tree_sha,
)
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_messages_service import (
    build_precommit_commit_message,
)


@dataclass(slots=True)
class CommitApplyOutcome:
    """Represent commit apply outcome data and behavior."""

    commit_sha: str
    recovered_from_conflict: bool = False


async def apply_bundle_commit(
    github_client,
    *,
    context,
    marker: str,
    changes,
    find_marker_commit_sha,
    logger,
) -> CommitApplyOutcome:
    """Apply bundle commit."""
    head_sha, base_tree_sha = await resolve_head_and_tree_sha(
        github_client,
        repo_full_name=context.repo_full_name,
        branch_name=context.default_branch,
    )
    tree_entries = await build_tree_entries(
        github_client,
        repo_full_name=context.repo_full_name,
        changes=changes,
        bundle_id=context.bundle_id,
    )
    created_tree = await github_client.create_tree(
        context.repo_full_name,
        tree=tree_entries,
        base_tree=base_tree_sha,
    )
    tree_sha = (created_tree.get("sha") or "").strip()
    if not tree_sha:
        raise ApiError(
            status_code=500,
            detail="Failed to create precommit bundle tree.",
            error_code="PRECOMMIT_TREE_CREATE_FAILED",
            details={"bundleId": context.bundle_id},
        )
    commit_payload = await github_client.create_commit(
        context.repo_full_name,
        message=build_precommit_commit_message(
            context.bundle_id, context.bundle.content_sha256
        ),
        tree=tree_sha,
        parents=[head_sha],
    )
    commit_sha = (commit_payload.get("sha") or "").strip()
    if not commit_sha:
        raise ApiError(
            status_code=500,
            detail="Failed to create precommit bundle commit.",
            error_code="PRECOMMIT_COMMIT_CREATE_FAILED",
            details={"bundleId": context.bundle_id},
        )
    try:
        await github_client.update_ref(
            context.repo_full_name,
            ref=f"heads/{context.default_branch}",
            sha=commit_sha,
            force=False,
        )
    except GithubError as exc:
        if exc.status_code in {409, 422}:
            recovered_sha = await find_marker_commit_sha(
                github_client,
                repo_full_name=context.repo_full_name,
                branch=context.default_branch,
                marker=marker,
            )
            if recovered_sha:
                logger.info(
                    "precommit_bundle_apply_recovered_after_ref_conflict",
                    extra={
                        "candidateSessionId": context.candidate_session_id,
                        "scenarioVersionId": context.scenario_version_id,
                        "taskId": context.task_id,
                        "repoFullName": context.repo_full_name,
                        "templateKey": context.template_key,
                        "bundleId": context.bundle_id,
                        "precommitSha": recovered_sha,
                    },
                )
                return CommitApplyOutcome(
                    commit_sha=recovered_sha, recovered_from_conflict=True
                )
        raise
    return CommitApplyOutcome(commit_sha=commit_sha)
