from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.settings import settings
from app.integrations.github import GithubError
from app.jobs import worker
from app.jobs.handlers import workspace_cleanup as cleanup_handler
from app.repositories.candidate_sessions import repository as cs_repo
from app.repositories.github_native.workspaces import repository as workspace_repo
from app.repositories.github_native.workspaces.models import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
    WorkspaceGroup,
)
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import JOB_STATUS_QUEUED, JOB_STATUS_SUCCEEDED
from app.services.submissions.workspace_cleanup_jobs import (
    WORKSPACE_CLEANUP_JOB_TYPE,
    build_workspace_cleanup_payload,
    workspace_cleanup_idempotency_key,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
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
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


async def _prepare_workspace(
    async_session: AsyncSession,
    *,
    created_at: datetime,
    completed_at: datetime | None,
    with_cutoff: bool,
) -> tuple[int, int, str, str]:
    recruiter = await create_recruiter(
        async_session,
        email=f"workspace-cleanup-int-{uuid4().hex}@test.com",
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
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
    return simulation.company_id, candidate_session.id, workspace.id, workspace_group.id


@pytest.mark.asyncio
async def test_workspace_cleanup_worker_archive_and_rerun_idempotent(
    async_session,
    monkeypatch,
):
    now = datetime.now(UTC).replace(microsecond=0)
    (
        company_id,
        candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=now - timedelta(days=45),
        completed_at=now - timedelta(days=35),
        with_cutoff=True,
    )

    class StubGithubClient:
        def __init__(self):
            self.remove_calls = 0
            self.archive_calls = 0
            self.delete_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            self.archive_calls += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            self.delete_calls += 1
            return {}

    github_client = StubGithubClient()
    session_maker = _session_maker(async_session)
    monkeypatch.setattr(cleanup_handler, "async_session_maker", session_maker)
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)

    first_job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=WORKSPACE_CLEANUP_JOB_TYPE,
        idempotency_key=workspace_cleanup_idempotency_key(
            company_id,
            run_key="run-1",
        ),
        payload_json=build_workspace_cleanup_payload(
            company_id=company_id,
            run_key="run-1",
        ),
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        max_attempts=2,
        next_run_at=now,
    )

    worker.register_handler(
        WORKSPACE_CLEANUP_JOB_TYPE,
        cleanup_handler.handle_workspace_cleanup,
    )
    first_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-archive-1",
        now=now,
    )
    assert first_handled is True

    first_refresh = await jobs_repo.get_by_id(async_session, first_job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_SUCCEEDED
    assert github_client.remove_calls == 1
    assert github_client.archive_calls == 1
    assert github_client.delete_calls == 0

    workspace_group = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    assert workspace_group.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert workspace_group.cleaned_at is not None
    assert workspace_group.access_revoked_at is not None

    second_job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=WORKSPACE_CLEANUP_JOB_TYPE,
        idempotency_key=workspace_cleanup_idempotency_key(
            company_id,
            run_key="run-2",
        ),
        payload_json=build_workspace_cleanup_payload(
            company_id=company_id,
            run_key="run-2",
        ),
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        max_attempts=2,
        next_run_at=now + timedelta(seconds=1),
    )

    second_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-archive-2",
        now=now + timedelta(seconds=1),
    )
    assert second_handled is True

    second_refresh = await jobs_repo.get_by_id(async_session, second_job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_SUCCEEDED
    assert github_client.remove_calls == 1
    assert github_client.archive_calls == 1
    assert github_client.delete_calls == 0


@pytest.mark.asyncio
async def test_workspace_cleanup_worker_delete_mode_with_opt_in(
    async_session,
    monkeypatch,
):
    now = datetime.now(UTC).replace(microsecond=0)
    (
        company_id,
        candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=now - timedelta(days=60),
        completed_at=now - timedelta(days=31),
        with_cutoff=False,
    )

    class StubGithubClient:
        def __init__(self):
            self.delete_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            raise AssertionError("archive_repo should not run in delete mode")

        async def delete_repo(self, *_args, **_kwargs):
            self.delete_calls += 1
            return {}

    github_client = StubGithubClient()
    session_maker = _session_maker(async_session)
    monkeypatch.setattr(cleanup_handler, "async_session_maker", session_maker)
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)
    monkeypatch.setattr(settings.github, "WORKSPACE_CLEANUP_MODE", "delete")
    monkeypatch.setattr(settings.github, "WORKSPACE_DELETE_ENABLED", True)

    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=WORKSPACE_CLEANUP_JOB_TYPE,
        idempotency_key=workspace_cleanup_idempotency_key(
            company_id,
            run_key="delete-run",
        ),
        payload_json=build_workspace_cleanup_payload(
            company_id=company_id,
            run_key="delete-run",
        ),
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        max_attempts=2,
        next_run_at=now,
    )

    worker.register_handler(
        WORKSPACE_CLEANUP_JOB_TYPE,
        cleanup_handler.handle_workspace_cleanup,
    )
    handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-delete",
        now=now,
    )
    assert handled is True

    refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert refresh is not None
    assert refresh.status == JOB_STATUS_SUCCEEDED
    assert github_client.delete_calls == 1

    workspace_group = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    assert workspace_group.cleanup_status == WORKSPACE_CLEANUP_STATUS_DELETED
    assert workspace_group.cleaned_at is not None


@pytest.mark.asyncio
async def test_workspace_cleanup_worker_retries_transient_collaborator_failure(
    async_session,
    monkeypatch,
):
    now = datetime.now(UTC).replace(microsecond=0)
    (
        company_id,
        candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=now - timedelta(days=5),
        completed_at=None,
        with_cutoff=True,
    )

    class FlakyGithubClient:
        def __init__(self):
            self.remove_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            if self.remove_calls == 1:
                raise GithubError("temporary failure", status_code=502)
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            raise AssertionError("archive_repo should not run before retention expiry")

        async def delete_repo(self, *_args, **_kwargs):
            raise AssertionError("delete_repo should not run before retention expiry")

    github_client = FlakyGithubClient()
    session_maker = _session_maker(async_session)
    monkeypatch.setattr(cleanup_handler, "async_session_maker", session_maker)
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)
    monkeypatch.setattr(settings.github, "WORKSPACE_RETENTION_DAYS", 365)

    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=WORKSPACE_CLEANUP_JOB_TYPE,
        idempotency_key=workspace_cleanup_idempotency_key(
            company_id,
            run_key="retry-run",
        ),
        payload_json=build_workspace_cleanup_payload(
            company_id=company_id,
            run_key="retry-run",
        ),
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        max_attempts=2,
        next_run_at=now,
    )

    worker.register_handler(
        WORKSPACE_CLEANUP_JOB_TYPE,
        cleanup_handler.handle_workspace_cleanup,
    )

    first_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-retry-1",
        now=now,
    )
    assert first_handled is True

    first_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_QUEUED
    assert first_refresh.attempt == 1

    second_handled = await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-retry-2",
        now=now + timedelta(seconds=1),
    )
    assert second_handled is True

    second_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_SUCCEEDED
    assert second_refresh.attempt == 2

    workspace_group = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    assert workspace_group.access_revoked_at is not None
    assert workspace_group.access_revocation_error is None
