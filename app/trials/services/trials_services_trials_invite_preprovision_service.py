"""Application module for trials services trials invite preprovision service workflows."""

from __future__ import annotations

import inspect
import logging

from app.config import settings
from app.integrations.github import GithubClient, GithubError
from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    resolve_workspace_key_for_task,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)

logger = logging.getLogger(__name__)


async def preprovision_workspaces(
    db,
    candidate_session,
    trial,
    scenario_version,
    tasks,
    github_client: GithubClient,
    *,
    now,
    fresh_candidate_session: bool = False,
) -> list[str]:
    """Execute preprovision workspaces."""
    repo_prefix = settings.github.GITHUB_REPO_PREFIX
    destination_owner = settings.github.GITHUB_ORG
    processed_workspace_keys: set[str] = set()
    provisioned_repo_full_names: list[str] = []
    ensure_workspace_params = inspect.signature(
        submission_service.ensure_workspace
    ).parameters
    supports_workspace_resolution = "workspace_resolution" in ensure_workspace_params
    supports_commit = "commit" in ensure_workspace_params
    supports_hydrate_precommit_bundle = (
        "hydrate_precommit_bundle" in ensure_workspace_params
    )
    for task in tasks:
        if task.day_index not in {2, 3} or not submission_service.is_code_task(task):
            continue
        workspace_key = resolve_workspace_key_for_task(task)
        if workspace_key and workspace_key in processed_workspace_keys:
            continue
        github_username = (
            getattr(candidate_session, "github_username", None) or ""
        ).strip()
        if not github_username:
            logger.info(
                "github_workspace_preprovision_skipped_missing_username",
                extra={
                    "trial_id": getattr(candidate_session, "trial_id", None),
                    "candidate_session_id": getattr(candidate_session, "id", None),
                    "task_id": task.id,
                    "day_index": task.day_index,
                },
            )
            continue
        try:
            ensure_workspace_kwargs = {
                "candidate_session": candidate_session,
                "trial": trial,
                "scenario_version": scenario_version,
                "task": task,
                "github_client": github_client,
                "github_username": github_username,
                "repo_prefix": repo_prefix,
                "destination_owner": destination_owner,
                "now": now,
                "bootstrap_empty_repo": True,
            }
            if (
                supports_workspace_resolution
                and fresh_candidate_session
                and workspace_key
            ):
                ensure_workspace_kwargs[
                    "workspace_resolution"
                ] = workspace_repo.WorkspaceResolution(
                    workspace_key=workspace_key,
                    uses_grouped_workspace=True,
                    workspace_group=None,
                    workspace_group_checked=True,
                )
            if supports_commit:
                ensure_workspace_kwargs["commit"] = False
            if supports_hydrate_precommit_bundle:
                ensure_workspace_kwargs["hydrate_precommit_bundle"] = False
            workspace = await submission_service.ensure_workspace(
                db, **ensure_workspace_kwargs
            )
            repo_full_name = getattr(workspace, "repo_full_name", None)
            if (
                repo_full_name
                and getattr(workspace, "_provisioned_repo_created", False)
                and repo_full_name not in provisioned_repo_full_names
            ):
                provisioned_repo_full_names.append(repo_full_name)
            if workspace_key:
                processed_workspace_keys.add(workspace_key)
        except Exception as exc:
            if provisioned_repo_full_names and not hasattr(
                exc, "provisioned_repo_full_names"
            ):
                exc.provisioned_repo_full_names = tuple(provisioned_repo_full_names)
            logger.error(
                "github_workspace_preprovision_failed",
                extra={
                    "trial_id": getattr(candidate_session, "trial_id", None),
                    "candidate_session_id": getattr(candidate_session, "id", None),
                    "task_id": task.id,
                    "day_index": task.day_index,
                    "repo_name": submission_service.build_repo_name(
                        prefix=repo_prefix,
                        candidate_session=candidate_session,
                        task=task,
                        workspace_key=workspace_key,
                    ),
                    "status_code": getattr(exc, "status_code", None),
                },
            )
            raise
    return provisioned_repo_full_names


__all__ = ["preprovision_workspaces", "GithubError"]
