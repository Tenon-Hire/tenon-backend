from __future__ import annotations

import pytest

from tests.shared.jobs.shared_jobs_workspace_cleanup_integration_utils import *


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
    assert await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-archive-1",
        now=now,
    )

    first_refresh = await jobs_repo.get_by_id(async_session, first_job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_SUCCEEDED
    assert (
        github_client.remove_calls,
        github_client.archive_calls,
        github_client.delete_calls,
    ) == (1, 1, 0)

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

    assert await worker.run_once(
        session_maker=session_maker,
        worker_id="workspace-cleanup-archive-2",
        now=now + timedelta(seconds=1),
    )

    second_refresh = await jobs_repo.get_by_id(async_session, second_job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_SUCCEEDED
    assert (
        github_client.remove_calls,
        github_client.archive_calls,
        github_client.delete_calls,
    ) == (1, 1, 0)
