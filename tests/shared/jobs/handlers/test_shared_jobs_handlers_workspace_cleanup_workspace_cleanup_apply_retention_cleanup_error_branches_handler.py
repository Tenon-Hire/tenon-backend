from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


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
async def test_workspace_cleanup_apply_retention_cleanup_delete_404_marks_deleted(
    async_session,
):
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

    class StubGithubClientDeleteMissing:
        async def delete_repo(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def archive_repo(self, *_args, **_kwargs):
            return {}

    now = datetime.now(UTC)
    result = await cleanup_handler._apply_retention_cleanup(
        StubGithubClientDeleteMissing(),
        record=record,
        now=now,
        cleanup_mode="delete",
        delete_enabled=True,
        job_id="job-f",
    )

    assert result == "deleted_repo_missing"
    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_DELETED
    assert record.cleaned_at == now
    assert record.cleanup_error is None
