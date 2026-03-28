"""Application module for submissions services submissions workspace existing service workflows."""

from __future__ import annotations

import contextlib
import json

from app.integrations.github.client import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service import (
    apply_precommit_bundle_if_available,
)


def _serialize_no_bundle_details(precommit_result: object) -> str | None:
    if getattr(precommit_result, "state", None) != "no_bundle":
        return None
    details = getattr(precommit_result, "details", None)
    if not isinstance(details, dict):
        return None
    payload = {"state": "no_bundle", **details}
    return json.dumps(payload, sort_keys=True)


async def ensure_existing_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str | None,
    workspace_resolution: workspace_repo.WorkspaceResolution | None = None,
    commit: bool = True,
    hydrate_precommit_bundle: bool = True,
) -> Workspace | None:
    """Ensure existing workspace."""
    task_day_index = getattr(task, "day_index", None)
    task_type = getattr(task, "type", None)
    task_identity: dict[str, int | str] = {}
    if task_day_index is not None and task_type is not None:
        task_identity["task_day_index"] = task_day_index
        task_identity["task_type"] = task_type
    existing = await workspace_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        workspace_resolution=workspace_resolution,
        **task_identity,
    )
    if not existing:
        return None
    if github_username:
        with contextlib.suppress(GithubError):
            await github_client.add_collaborator(
                existing.repo_full_name, github_username
            )
    if not hydrate_precommit_bundle or getattr(existing, "precommit_sha", None):
        return existing
    precommit_result = await apply_precommit_bundle_if_available(
        db,
        github_client=github_client,
        candidate_session=candidate_session,
        task=task,
        repo_full_name=existing.repo_full_name,
        default_branch=existing.default_branch,
        base_template_sha=existing.base_template_sha,
        existing_precommit_sha=getattr(existing, "precommit_sha", None),
    )
    if (
        precommit_result.precommit_sha
        and getattr(existing, "precommit_sha", None) != precommit_result.precommit_sha
    ):
        if commit:
            return await workspace_repo.set_precommit_sha(
                db,
                workspace=existing,
                precommit_sha=precommit_result.precommit_sha,
            )
        return await workspace_repo.set_precommit_sha(
            db,
            workspace=existing,
            precommit_sha=precommit_result.precommit_sha,
            commit=False,
            refresh=False,
        )
    no_bundle_details_json = _serialize_no_bundle_details(precommit_result)
    if no_bundle_details_json and (
        getattr(existing, "precommit_details_json", None) != no_bundle_details_json
    ):
        if commit:
            return await workspace_repo.set_precommit_details(
                db,
                workspace=existing,
                precommit_details_json=no_bundle_details_json,
            )
        return await workspace_repo.set_precommit_details(
            db,
            workspace=existing,
            precommit_details_json=no_bundle_details_json,
            commit=False,
            refresh=False,
        )
    return existing
