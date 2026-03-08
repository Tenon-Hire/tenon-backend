from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.domains import CandidateSession, Task
from app.domains.submissions.exceptions import WorkspaceMissing
from app.integrations.github.client import GithubClient, GithubError
from app.repositories.github_native.workspaces import repository as workspace_repo
from app.repositories.github_native.workspaces.models import Workspace, WorkspaceGroup
from app.repositories.github_native.workspaces.workspace_keys import (
    CODING_WORKSPACE_KEY,
    resolve_workspace_key_for_task,
)
from app.services.submissions.workspace_repo_state import (
    add_collaborator_if_needed,
    fetch_base_template_sha,
)
from app.services.submissions.workspace_template_repo import generate_template_repo

logger = logging.getLogger(__name__)


async def provision_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    template_default_owner: str | None,
    now: datetime,
) -> Workspace:
    workspace_key = resolve_workspace_key_for_task(task)
    if await workspace_repo.session_uses_grouped_workspace(
        db,
        candidate_session_id=candidate_session.id,
        workspace_key=workspace_key,
    ):
        if (
            workspace_key == CODING_WORKSPACE_KEY
            and getattr(task, "day_index", None) == 3
        ):
            existing_group = await workspace_repo.get_workspace_group(
                db,
                candidate_session_id=candidate_session.id,
                workspace_key=workspace_key,
            )
            if existing_group is None:
                raise WorkspaceMissing(
                    detail=(
                        "Workspace not initialized. Call Day 2 /codespace/init first."
                    )
                )
        return await _provision_grouped_workspace(
            db,
            candidate_session=candidate_session,
            task=task,
            workspace_key=workspace_key,
            github_client=github_client,
            github_username=github_username,
            repo_prefix=repo_prefix,
            template_default_owner=template_default_owner,
            now=now,
        )

    (
        template_repo,
        repo_full_name,
        default_branch,
        repo_id,
    ) = await generate_template_repo(
        github_client=github_client,
        candidate_session=candidate_session,
        task=task,
        repo_prefix=repo_prefix,
        template_default_owner=template_default_owner,
        workspace_key=None,
    )
    base_template_sha = await fetch_base_template_sha(
        github_client, repo_full_name, default_branch
    )
    await add_collaborator_if_needed(github_client, repo_full_name, github_username)
    return await workspace_repo.create_workspace(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        template_repo_full_name=template_repo,
        repo_full_name=repo_full_name,
        repo_id=repo_id,
        default_branch=default_branch,
        base_template_sha=base_template_sha,
        created_at=now,
    )


async def _provision_grouped_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    template_default_owner: str | None,
    now: datetime,
) -> Workspace:
    group, repo_id = await _get_or_create_workspace_group(
        db,
        candidate_session=candidate_session,
        task=task,
        workspace_key=workspace_key,
        github_client=github_client,
        github_username=github_username,
        repo_prefix=repo_prefix,
        template_default_owner=template_default_owner,
        now=now,
    )
    existing = await workspace_repo.get_by_workspace_group_id(
        db, workspace_group_id=group.id
    )
    if existing is not None:
        await add_collaborator_if_needed(
            github_client, existing.repo_full_name, github_username
        )
        return existing

    try:
        return await workspace_repo.create_workspace(
            db,
            workspace_group_id=group.id,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            template_repo_full_name=group.template_repo_full_name,
            repo_full_name=group.repo_full_name,
            repo_id=repo_id,
            default_branch=group.default_branch,
            base_template_sha=group.base_template_sha,
            created_at=now,
        )
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
        if existing is None:  # pragma: no cover - defensive guard
            raise
        return existing


async def _get_or_create_workspace_group(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    template_default_owner: str | None,
    now: datetime,
) -> tuple[WorkspaceGroup, int | None]:
    existing = await workspace_repo.get_workspace_group(
        db,
        candidate_session_id=candidate_session.id,
        workspace_key=workspace_key,
    )
    if existing is not None:
        await add_collaborator_if_needed(
            github_client, existing.repo_full_name, github_username
        )
        return existing, None

    try:
        (
            template_repo,
            repo_full_name,
            default_branch,
            repo_id,
        ) = await generate_template_repo(
            github_client=github_client,
            candidate_session=candidate_session,
            task=task,
            repo_prefix=repo_prefix,
            template_default_owner=template_default_owner,
            workspace_key=workspace_key,
        )
    except GithubError as exc:
        if exc.status_code == 422:
            existing = await workspace_repo.get_workspace_group(
                db,
                candidate_session_id=candidate_session.id,
                workspace_key=workspace_key,
            )
            if existing is not None:
                logger.warning(
                    "workspace_group_duplicate_create_attempt",
                    extra={
                        "candidateSessionId": candidate_session.id,
                        "workspaceKey": workspace_key,
                        "repoFullName": existing.repo_full_name,
                    },
                )
                await add_collaborator_if_needed(
                    github_client, existing.repo_full_name, github_username
                )
                return existing, None
        raise

    base_template_sha = await fetch_base_template_sha(
        github_client, repo_full_name, default_branch
    )
    await add_collaborator_if_needed(github_client, repo_full_name, github_username)

    try:
        group = await workspace_repo.create_workspace_group(
            db,
            candidate_session_id=candidate_session.id,
            workspace_key=workspace_key,
            template_repo_full_name=template_repo,
            repo_full_name=repo_full_name,
            default_branch=default_branch,
            base_template_sha=base_template_sha,
            created_at=now,
        )
        logger.info(
            "workspace_group_created",
            extra={
                "candidateSessionId": candidate_session.id,
                "workspaceKey": workspace_key,
                "repoFullName": repo_full_name,
            },
        )
        return group, repo_id
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "workspace_group_duplicate_create_attempt",
            extra={
                "candidateSessionId": candidate_session.id,
                "workspaceKey": workspace_key,
                "repoFullName": repo_full_name,
            },
        )
        existing = await workspace_repo.get_workspace_group(
            db,
            candidate_session_id=candidate_session.id,
            workspace_key=workspace_key,
        )
        if existing is None:  # pragma: no cover - defensive guard
            raise
        await add_collaborator_if_needed(
            github_client, existing.repo_full_name, github_username
        )
        return existing, None
