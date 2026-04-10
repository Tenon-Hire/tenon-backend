from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.config import settings
from app.integrations.github import GithubError
from app.shared.jobs import worker
from app.shared.jobs.handlers import (
    WORKSPACE_CLEANUP_JOB_TYPE,
)
from app.shared.jobs.handlers import (
    workspace_cleanup as cleanup_handler,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_cleanup_status_constants import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_group_model import (
    WorkspaceGroup,
)
from app.submissions.services.submissions_services_submissions_workspace_cleanup_jobs_service import (
    build_workspace_cleanup_payload,
    workspace_cleanup_idempotency_key,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.fixture(autouse=True)
def _clear_job_handlers():
    worker.clear_handlers()
    yield
    worker.clear_handlers()


@pytest.fixture(autouse=True)
def _cleanup_settings_defaults(monkeypatch):
    monkeypatch.setattr(settings.github, "WORKSPACE_RETENTION_DAYS", 30)
    monkeypatch.setattr(settings.github, "WORKSPACE_CLEANUP_MODE", "archive")
    monkeypatch.setattr(settings.github, "WORKSPACE_DELETE_ENABLED", False)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


async def _prepare_workspace(
    async_session: AsyncSession,
    *,
    created_at: datetime,
    completed_at: datetime | None,
    with_cutoff: bool,
) -> tuple[int, int, str, str]:
    talent_partner = await create_talent_partner(
        async_session,
        email=f"workspace-cleanup-int-{uuid4().hex}@test.com",
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        completed_at=completed_at,
        with_default_schedule=True,
    )
    candidate_session.github_username = "octocat"

    day2_task = next(task for task in tasks if task.day_index == 2)
    workspace_group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name=f"org/workspace-{candidate_session.id}",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    workspace = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=workspace_group.id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name=workspace_group.template_repo_full_name,
        repo_full_name=workspace_group.repo_full_name,
        repo_id=1234,
        default_branch=workspace_group.default_branch,
        base_template_sha=workspace_group.base_template_sha,
        created_at=created_at,
    )

    if with_cutoff:
        await cs_repo.create_day_audit_once(
            async_session,
            candidate_session_id=candidate_session.id,
            day_index=2,
            cutoff_at=created_at,
            cutoff_commit_sha="cutoff-sha",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=True,
        )
    await async_session.commit()
    return trial.company_id, candidate_session.id, workspace.id, workspace_group.id


__all__ = [name for name in globals() if not name.startswith("__")]
