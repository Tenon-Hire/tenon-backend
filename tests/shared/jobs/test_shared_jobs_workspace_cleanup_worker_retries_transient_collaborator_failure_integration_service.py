from __future__ import annotations

import pytest

from tests.shared.jobs.shared_jobs_workspace_cleanup_integration_utils import *


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
