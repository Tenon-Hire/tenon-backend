"""Application module for submissions services submissions workspace creation grouped service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_service import (
    get_or_create_workspace_group,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_grouped_hydration_service import (
    hydrate_existing_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_records_service import (
    build_codespace_url,
)

logger = logging.getLogger(__name__)


async def provision_grouped_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    destination_owner: str | None,
    now: datetime,
    existing_group: WorkspaceGroup | None = None,
    commit: bool = True,
    hydrate_precommit_bundle: bool = True,
    existing_checked: bool = False,
    workspace_group_checked: bool = False,
    bootstrap_empty_repo: bool = False,
    trial=None,
    scenario_version=None,
) -> Workspace:
    """Execute provision grouped workspace."""
    group_result = await get_or_create_workspace_group(
        db,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=task,
        workspace_key=workspace_key,
        github_client=github_client,
        github_username=github_username,
        repo_prefix=repo_prefix,
        destination_owner=destination_owner,
        now=now,
        existing_group=existing_group,
        commit=commit,
        workspace_group_checked=workspace_group_checked,
        bootstrap_empty_repo=bootstrap_empty_repo,
    )
    if isinstance(group_result, tuple) and len(group_result) == 2:
        group, repo_id = group_result
        codespace_name = None
        codespace_state = None
        codespace_url = None
    else:
        (
            group,
            repo_id,
            codespace_name,
            codespace_state,
            codespace_url,
        ) = group_result
    existing = (
        None
        if existing_checked
        else await workspace_repo.get_by_workspace_group_id(
            db, workspace_group_id=group.id
        )
    )
    if existing is not None:
        return await hydrate_existing_workspace(
            db,
            existing,
            candidate_session,
            task,
            github_client,
            github_username,
            hydrate_precommit_bundle,
            commit,
            ensure_collaborator=True,
        )
    try:
        create_workspace_kwargs = {
            "workspace_group_id": group.id,
            "candidate_session_id": candidate_session.id,
            "task_id": task.id,
            "template_repo_full_name": group.template_repo_full_name,
            "repo_full_name": group.repo_full_name,
            "repo_id": repo_id,
            "default_branch": group.default_branch,
            "base_template_sha": group.base_template_sha,
            "codespace_url": codespace_url
            if bootstrap_empty_repo and codespace_url
            else build_codespace_url(group.repo_full_name),
            "codespace_name": codespace_name if bootstrap_empty_repo else None,
            "codespace_state": codespace_state if bootstrap_empty_repo else None,
            "created_at": now,
        }
        if not commit:
            create_workspace_kwargs["commit"] = False
            create_workspace_kwargs["refresh"] = False
        created = await workspace_repo.create_workspace(db, **create_workspace_kwargs)
        result = await hydrate_existing_workspace(
            db,
            created,
            candidate_session,
            task,
            github_client,
            github_username,
            hydrate_precommit_bundle,
            commit,
        )
        result._provisioned_repo_created = True
        return result
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "workspace_duplicate_create_attempt",
            extra={
                "candidateSessionId": candidate_session.id,
                "workspaceKey": workspace_key,
                "repoFullName": group.repo_full_name,
            },
        )
        existing = await workspace_repo.get_by_workspace_group_id(
            db, workspace_group_id=group.id
        )
        if existing is None:
            raise
        return await hydrate_existing_workspace(
            db,
            existing,
            candidate_session,
            task,
            github_client,
            github_username,
            hydrate_precommit_bundle,
            commit,
        )
