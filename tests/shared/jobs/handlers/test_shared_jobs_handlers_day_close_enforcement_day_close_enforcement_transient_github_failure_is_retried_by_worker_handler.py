from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_day_close_enforcement_transient_github_failure_is_retried_by_worker(
    async_session,
    monkeypatch,
):
    (
        trial,
        candidate_session,
        _day2_task,
        _cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)
    now = datetime.now(UTC).replace(microsecond=0)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type=DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        idempotency_key=day_close_enforcement_idempotency_key(candidate_session.id, 2),
        payload_json=payload,
        company_id=trial.company_id,
        candidate_session_id=candidate_session.id,
        max_attempts=2,
        next_run_at=now,
    )

    class FlakyGithubClient:
        def __init__(self):
            self.remove_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            if self.remove_calls == 1:
                raise GithubError("temporary github failure", status_code=502)
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "worker-cutoff-sha"}}

    client = FlakyGithubClient()
    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(enforcement_handler, "get_github_client", lambda: client)

    worker.register_handler(
        DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        enforcement_handler.handle_day_close_enforcement,
    )

    first_handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-cutoff-1",
        now=now,
    )
    assert first_handled is True
    first_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert first_refresh is not None
    assert first_refresh.status == JOB_STATUS_QUEUED
    assert first_refresh.attempt == 1

    second_handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-cutoff-2",
        now=now + timedelta(seconds=1),
    )
    assert second_handled is True
    second_refresh = await jobs_repo.get_by_id(async_session, job.id)
    assert second_refresh is not None
    assert second_refresh.status == JOB_STATUS_SUCCEEDED
    assert second_refresh.attempt == 2

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "worker-cutoff-sha"
