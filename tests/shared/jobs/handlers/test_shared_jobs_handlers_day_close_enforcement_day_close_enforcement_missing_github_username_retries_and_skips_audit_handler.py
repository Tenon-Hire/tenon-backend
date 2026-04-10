from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_day_close_enforcement_missing_github_username_retries_and_skips_audit(
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
    candidate_session.github_username = None
    await async_session.commit()

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

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "should-not-be-used"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: StubGithubClient(),
    )
    worker.register_handler(
        DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        enforcement_handler.handle_day_close_enforcement,
    )

    handled = await worker.run_once(
        session_maker=_session_maker(async_session),
        worker_id="worker-missing-identity-1",
        now=now,
    )

    assert handled is True
    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.attempt == 1
    assert "day_close_enforcement_missing_github_username" in (
        refreshed.last_error or ""
    )

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is None
