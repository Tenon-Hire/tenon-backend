"""Workspace provisioning helpers for submissions.

This file exceeds 50 LOC because the GitHub flow requires several IO steps that
must remain together to preserve behavior without scattering logic.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession, Task
from app.domains.github_native.client import GithubClient, GithubError
from app.domains.github_native.workspaces import repository as workspace_repo
from app.domains.github_native.workspaces.workspace import Workspace
from app.domains.submissions.services.github_user import validate_github_username
from app.domains.submissions.services.repo_naming import (
    build_repo_name,
    validate_repo_full_name,
)


async def ensure_workspace(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str,
    repo_prefix: str,
    template_default_owner: str | None,
    now: datetime,
) -> Workspace:
    """Fetch or create a workspace for the candidate+task."""
    if github_username:
        validate_github_username(github_username)

    existing = await workspace_repo.get_by_session_and_task(
        db, candidate_session_id=candidate_session.id, task_id=task.id
    )
    if existing:
        if github_username:
            with contextlib.suppress(GithubError):
                await github_client.add_collaborator(
                    existing.repo_full_name, github_username
                )
        return existing

    template_repo = (task.template_repo or "").strip()
    if not template_repo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task template repository is not configured",
        )
    validate_repo_full_name(template_repo)

    new_repo_name = build_repo_name(
        prefix=repo_prefix, candidate_session=candidate_session, task=task
    )
    template_owner = template_repo.split("/")[0] if "/" in template_repo else None
    generated = await github_client.generate_repo_from_template(
        template_full_name=template_repo,
        new_repo_name=new_repo_name,
        owner=template_owner or template_default_owner,
        private=True,
    )

    repo_full_name = generated.get("full_name") or ""
    default_branch = generated.get("default_branch") or generated.get("master_branch")
    repo_id = generated.get("id")
    validate_repo_full_name(repo_full_name)

    base_template_sha = None
    try:
        branch_data = await github_client.get_branch(
            repo_full_name, default_branch or "main"
        )
        base_template_sha = (branch_data.get("commit") or {}).get("sha")
    except GithubError:
        base_template_sha = None

    if github_username:
        with contextlib.suppress(GithubError):
            await github_client.add_collaborator(repo_full_name, github_username)

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
