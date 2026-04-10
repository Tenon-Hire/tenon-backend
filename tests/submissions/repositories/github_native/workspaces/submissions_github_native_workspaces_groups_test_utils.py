from __future__ import annotations

from datetime import UTC, datetime

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository import (
    CODING_WORKSPACE_KEY,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


async def seed_candidate_workspace_session(async_session, *, email: str):
    talent_partner = await create_talent_partner(async_session, email=email)
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
    )
    return candidate_session, tasks


def utc_now() -> datetime:
    return datetime.now(UTC)


async def create_coding_workspace_group(async_session, *, candidate_session_id, task):
    return await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session_id,
        workspace_key=CODING_WORKSPACE_KEY,
        template_repo_full_name=task.template_repo or "org/template",
        repo_full_name="org/session-coding",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=utc_now(),
    )


async def create_workspace(
    async_session, *, candidate_session_id, task, repo_id, group=None
):
    kwargs = {
        "candidate_session_id": candidate_session_id,
        "task_id": task.id,
        "template_repo_full_name": task.template_repo or "org/template",
        "repo_full_name": "org/legacy-day2",
        "repo_id": repo_id,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "created_at": utc_now(),
    }
    if group is not None:
        kwargs.update(
            {
                "workspace_group_id": group.id,
                "template_repo_full_name": group.template_repo_full_name,
                "repo_full_name": group.repo_full_name,
                "default_branch": group.default_branch,
                "base_template_sha": group.base_template_sha,
            }
        )
    return await workspace_repo.create_workspace(async_session, **kwargs)
