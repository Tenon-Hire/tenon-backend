from __future__ import annotations

import pytest

from tests.shared.jobs.shared_jobs_workspace_cleanup_integration_utils import *


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
