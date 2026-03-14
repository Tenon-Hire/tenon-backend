from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.settings import settings
from app.integrations.github import GithubError
from app.jobs.handlers import workspace_cleanup as cleanup_handler
from app.repositories.candidate_sessions import repository as cs_repo
from app.repositories.github_native.workspaces import repository as workspace_repo
from app.repositories.github_native.workspaces.models import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
    WORKSPACE_CLEANUP_STATUS_FAILED,
    WORKSPACE_CLEANUP_STATUS_PENDING,
    Workspace,
    WorkspaceGroup,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture(autouse=True)
def _cleanup_settings_defaults(monkeypatch):
    monkeypatch.setattr(settings.github, "WORKSPACE_RETENTION_DAYS", 30)
    monkeypatch.setattr(settings.github, "WORKSPACE_CLEANUP_MODE", "archive")
    monkeypatch.setattr(settings.github, "WORKSPACE_DELETE_ENABLED", False)


async def _prepare_workspace(
    async_session: AsyncSession,
    *,
    created_at: datetime,
    completed_at: datetime | None = None,
    session_status: str = "completed",
    with_cutoff: bool = False,
    github_username: str | None = "octocat",
    use_group: bool = False,
) -> tuple[int, int, str, str | None]:
    recruiter = await create_recruiter(
        async_session,
        email=f"workspace-cleanup-handler-{uuid4().hex}@test.com",
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status=session_status,
        with_default_schedule=True,
        completed_at=completed_at,
    )
    candidate_session.github_username = github_username
    day2_task = next(task for task in tasks if task.day_index == 2)

    workspace_group_id: str | None = None
    if use_group:
        group = await workspace_repo.create_workspace_group(
            async_session,
            candidate_session_id=candidate_session.id,
            workspace_key="coding",
            template_repo_full_name="org/template-repo",
            repo_full_name="org/candidate-repo",
            default_branch="main",
            base_template_sha="base-sha",
            created_at=created_at,
        )
        workspace_group_id = group.id

    workspace = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=workspace_group_id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/candidate-repo",
        repo_id=1234,
        default_branch="main",
        base_template_sha="base-sha",
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
    return simulation.company_id, candidate_session.id, workspace.id, workspace_group_id


async def _load_cleanup_record(
    async_session: AsyncSession,
    *,
    workspace_id: str,
    workspace_group_id: str | None,
):
    if workspace_group_id is not None:
        return (
            await async_session.execute(
                select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
            )
        ).scalar_one()
    return (
        await async_session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_workspace_cleanup_retention_boundary_helpers():
    anchor = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expires_0 = cleanup_handler._retention_expires_at(anchor, retention_days=0)
    expires_1 = cleanup_handler._retention_expires_at(anchor, retention_days=1)
    expires_7 = cleanup_handler._retention_expires_at(anchor, retention_days=7)

    assert cleanup_handler._retention_expired(now=anchor, expires_at=expires_0) is False
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(seconds=1),
            expires_at=expires_0,
        )
        is True
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=1),
            expires_at=expires_1,
        )
        is False
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=1, seconds=1),
            expires_at=expires_1,
        )
        is True
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=7, seconds=1),
            expires_at=expires_7,
        )
        is True
    )


@pytest.mark.asyncio
async def test_workspace_cleanup_helper_branches_cover_edge_cases():
    assert cleanup_handler._parse_positive_int(True) is None
    assert cleanup_handler._parse_positive_int("9") == 9
    assert cleanup_handler._parse_positive_int("abc") is None

    aware = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    assert cleanup_handler._normalize_datetime(aware) == aware

    assert (
        cleanup_handler._workspace_error_code(GithubError("err", status_code=None))
        == "github_request_failed"
    )
    assert cleanup_handler._workspace_error_code(RuntimeError("boom")) == "RuntimeError"
    assert (
        cleanup_handler._is_transient_github_error(
            GithubError("unknown transport", status_code=None)
        )
        is True
    )
    assert cleanup_handler._cleanup_target_repo_key(
        candidate_session_id=1,
        repo_full_name=None,
        fallback_id="fallback",
    ) == (1, "id:fallback")


@pytest.mark.asyncio
async def test_workspace_cleanup_invalid_payload_is_skipped():
    result = await cleanup_handler.handle_workspace_cleanup({"companyId": "invalid"})
    assert result == {"status": "skipped_invalid_payload", "companyId": None}


@pytest.mark.asyncio
async def test_workspace_cleanup_load_sessions_with_cutoff_empty(async_session):
    session_ids = await cleanup_handler._load_sessions_with_cutoff(
        async_session,
        candidate_session_ids=[],
    )
    assert session_ids == set()


@pytest.mark.asyncio
async def test_workspace_cleanup_group_target_dedupes_same_repo(async_session):
    recruiter = await create_recruiter(
        async_session,
        email=f"workspace-cleanup-group-dedupe-{uuid4().hex}@test.com",
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        with_default_schedule=True,
    )
    created_at = datetime.now(UTC) - timedelta(days=60)
    await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="other",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await async_session.commit()

    targets = await cleanup_handler._list_company_cleanup_targets(
        async_session,
        company_id=simulation.company_id,
    )
    assert len(targets) == 1


@pytest.mark.asyncio
async def test_workspace_cleanup_enforce_revocation_missing_field_branches(
    async_session,
):
    created_at = datetime.now(UTC) - timedelta(days=30)
    (
        _company_id,
        candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    record = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    candidate_session = (
        await async_session.execute(
            select(cleanup_handler.CandidateSession).where(
                cleanup_handler.CandidateSession.id == candidate_session_id
            )
        )
    ).scalar_one()
    now = datetime.now(UTC)

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

    record.repo_full_name = "   "
    missing_repo = await cleanup_handler._enforce_collaborator_revocation(
        StubGithubClient(),
        record=record,
        candidate_session=candidate_session,
        should_revoke=True,
        now=now,
        job_id="job-1",
    )
    assert missing_repo == "missing_repo"
    assert record.access_revocation_error == "missing_repo_full_name"

    record.repo_full_name = "org/real-repo"
    candidate_session.github_username = ""
    missing_username = await cleanup_handler._enforce_collaborator_revocation(
        StubGithubClient(),
        record=record,
        candidate_session=candidate_session,
        should_revoke=True,
        now=now,
        job_id="job-2",
    )
    assert missing_username == "missing_github_username"
    assert record.access_revocation_error == "missing_github_username"


@pytest.mark.asyncio
async def test_workspace_cleanup_apply_retention_cleanup_error_branches(async_session):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        _company_id,
        _candidate_session_id,
        _workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )
    record = (
        await async_session.execute(
            select(WorkspaceGroup).where(WorkspaceGroup.id == workspace_group_id)
        )
    ).scalar_one()
    now = datetime.now(UTC)

    class StubGithubClientMissing:
        async def archive_repo(self, *_args, **_kwargs):
            return {}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    record.repo_full_name = "   "
    missing_repo = await cleanup_handler._apply_retention_cleanup(
        StubGithubClientMissing(),
        record=record,
        now=now,
        cleanup_mode="archive",
        delete_enabled=False,
        job_id="job-a",
    )
    assert missing_repo == "failed_missing_repo"

    record.repo_full_name = "org/repo"
    record.template_repo_full_name = "org/repo"
    protected = await cleanup_handler._apply_retention_cleanup(
        StubGithubClientMissing(),
        record=record,
        now=now,
        cleanup_mode="archive",
        delete_enabled=False,
        job_id="job-b",
    )
    assert protected == "failed_protected_template_repo"

    record.template_repo_full_name = "org/template-repo"

    class StubGithubClientDeletePermanent:
        async def delete_repo(self, *_args, **_kwargs):
            raise GithubError("forbidden", status_code=403)

        async def archive_repo(self, *_args, **_kwargs):
            return {}

    delete_permanent = await cleanup_handler._apply_retention_cleanup(
        StubGithubClientDeletePermanent(),
        record=record,
        now=now,
        cleanup_mode="delete",
        delete_enabled=True,
        job_id="job-c",
    )
    assert delete_permanent == "failed_delete_permanent"

    class StubGithubClientDeleteTransient:
        async def delete_repo(self, *_args, **_kwargs):
            raise GithubError("temporary", status_code=502)

        async def archive_repo(self, *_args, **_kwargs):
            return {}

    with pytest.raises(cleanup_handler._WorkspaceCleanupRetryableError):
        await cleanup_handler._apply_retention_cleanup(
            StubGithubClientDeleteTransient(),
            record=record,
            now=now,
            cleanup_mode="delete",
            delete_enabled=True,
            job_id="job-d",
        )

    class StubGithubClientArchiveTransient:
        async def archive_repo(self, *_args, **_kwargs):
            raise GithubError("temporary", status_code=503)

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    with pytest.raises(cleanup_handler._WorkspaceCleanupRetryableError):
        await cleanup_handler._apply_retention_cleanup(
            StubGithubClientArchiveTransient(),
            record=record,
            now=now,
            cleanup_mode="archive",
            delete_enabled=False,
            job_id="job-e",
        )


@pytest.mark.asyncio
async def test_workspace_cleanup_unknown_cleanup_status_is_counted_pending(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        _workspace_id,
        _workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=False,
    )

    async def _fake_apply_retention_cleanup(*_args, **_kwargs):
        return "unknown_status"

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler,
        "_apply_retention_cleanup",
        _fake_apply_retention_cleanup,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})
    assert result["pending"] == 1


@pytest.mark.asyncio
async def test_workspace_cleanup_unexpected_exception_marks_failed_and_reraises(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )

    async def _raise_unexpected(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler,
        "_enforce_collaborator_revocation",
        _raise_unexpected,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    with pytest.raises(ValueError, match="boom"):
        await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "ValueError"


@pytest.mark.asyncio
async def test_workspace_cleanup_delete_mode_requires_guard(async_session, monkeypatch):
    created_at = datetime.now(UTC) - timedelta(days=40)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=False,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            raise AssertionError("delete_repo should not be called without guard")

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )
    monkeypatch.setattr(settings.github, "WORKSPACE_CLEANUP_MODE", "delete")
    monkeypatch.setattr(settings.github, "WORKSPACE_DELETE_ENABLED", False)

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["failed"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "delete_mode_disabled"


@pytest.mark.asyncio
async def test_workspace_cleanup_already_cleaned_is_noop(async_session, monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    created_at = now - timedelta(days=40)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )
    cleanup_record = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    cleanup_record.cleanup_status = WORKSPACE_CLEANUP_STATUS_ARCHIVED
    cleanup_record.cleaned_at = now - timedelta(days=1)
    await async_session.commit()

    calls = {"archive": 0, "delete": 0}

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            calls["archive"] += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            calls["delete"] += 1
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["alreadyCleaned"] == 1
    assert calls == {"archive": 0, "delete": 0}


@pytest.mark.asyncio
async def test_workspace_cleanup_collaborator_already_removed_is_noop(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            raise GithubError("not found", status_code=404)

        async def archive_repo(self, *_args, **_kwargs):
            raise AssertionError(
                "archive_repo should not run for non-expired workspace"
            )

        async def delete_repo(self, *_args, **_kwargs):
            raise AssertionError("delete_repo should not run for non-expired workspace")

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["revoked"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.access_revoked_at is not None
    assert stored.access_revocation_error is None


@pytest.mark.asyncio
async def test_workspace_cleanup_transient_github_failure_is_retryable(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            raise GithubError("temporary failure", status_code=502)

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    with pytest.raises(RuntimeError, match="github_status_502"):
        await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_attempted_at is not None
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.access_revocation_error == "github_status_502"


@pytest.mark.asyncio
async def test_workspace_cleanup_archive_missing_repo_maps_to_deleted(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=40)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            raise GithubError("not found", status_code=404)

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["deleted"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_DELETED
    assert stored.cleaned_at is not None
    assert stored.cleanup_error is None


@pytest.mark.asyncio
async def test_workspace_cleanup_archive_permanent_failure_is_terminal(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=40)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            raise GithubError("forbidden", status_code=403)

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["failed"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "github_status_403"


@pytest.mark.asyncio
async def test_workspace_cleanup_skips_active_session_even_when_retention_expired(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        session_status="in_progress",
        completed_at=None,
        use_group=True,
    )

    calls = {"archive": 0, "delete": 0}

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            calls["archive"] += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            calls["delete"] += 1
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["pending"] == 1
    assert result["skippedActive"] == 1
    assert calls == {"archive": 0, "delete": 0}
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_PENDING
    assert stored.cleaned_at is None


@pytest.mark.asyncio
async def test_workspace_cleanup_revocation_terminal_failure_blocks_cleanup(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    calls = {"archive": 0}

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            raise GithubError("forbidden", status_code=403)

        async def archive_repo(self, *_args, **_kwargs):
            calls["archive"] += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["failed"] == 1
    assert calls["archive"] == 0
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.access_revocation_error == "github_status_403"
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "github_status_403"
    assert stored.cleaned_at is None


@pytest.mark.asyncio
async def test_workspace_cleanup_rerun_after_revocation_failure_is_idempotent(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    class FlakyGithubClient:
        def __init__(self):
            self.remove_calls = 0
            self.archive_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            if self.remove_calls == 1:
                raise GithubError("forbidden", status_code=403)
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            self.archive_calls += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    github_client = FlakyGithubClient()
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)

    first = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})
    second = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert first["failed"] == 1
    assert second["archived"] == 1
    assert github_client.remove_calls == 2
    assert github_client.archive_calls == 1

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert stored.access_revocation_error is None
    assert stored.cleanup_error is None


@pytest.mark.asyncio
async def test_workspace_cleanup_uses_group_as_canonical_and_skips_duplicate_legacy(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session,
        email=f"workspace-cleanup-canonical-{uuid4().hex}@test.com",
    )
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        with_default_schedule=True,
    )

    created_at = datetime.now(UTC) - timedelta(days=60)
    group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )

    day2_task = next(task for task in tasks if task.day_index == 2)
    day3_task = next(task for task in tasks if task.day_index == 3)

    await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=group.id,
        candidate_session_id=candidate_session.id,
        task_id=day2_task.id,
        template_repo_full_name=group.template_repo_full_name,
        repo_full_name=group.repo_full_name,
        repo_id=999,
        default_branch=group.default_branch,
        base_template_sha=group.base_template_sha,
        created_at=created_at,
    )
    legacy = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=None,
        candidate_session_id=candidate_session.id,
        task_id=day3_task.id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/shared-repo",
        repo_id=1000,
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await async_session.commit()

    class StubGithubClient:
        def __init__(self):
            self.archive_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            self.archive_calls += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    github_client = StubGithubClient()
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)

    result = await cleanup_handler.handle_workspace_cleanup(
        {"companyId": simulation.company_id}
    )

    await async_session.refresh(group)
    await async_session.refresh(legacy)
    group_stored = group
    legacy_stored = legacy

    assert result["archived"] == 1
    assert result["candidateCount"] == 1
    assert github_client.archive_calls == 1
    assert group_stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert legacy_stored.cleanup_status is None
