from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_handle_day_close_enforcement_is_idempotent_and_no_overwrite(
    async_session,
    monkeypatch,
):
    (
        _trial,
        candidate_session,
        _day2_task,
        cutoff_at,
        payload,
    ) = await _prepare_code_day_context(async_session)

    class FirstClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def get_repo(self, *_args, **_kwargs):
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "first-sha"}}

    monkeypatch.setattr(
        enforcement_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: FirstClient(),
    )
    first = await enforcement_handler.handle_day_close_enforcement(payload)
    assert first["status"] == "cutoff_persisted"

    class SecondClient:
        def __init__(self):
            self.calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.calls += 1
            return {}

        async def get_repo(self, *_args, **_kwargs):
            self.calls += 1
            return {"default_branch": "main"}

        async def get_branch(self, *_args, **_kwargs):
            self.calls += 1
            return {"commit": {"sha": "second-sha"}}

    second_client = SecondClient()
    monkeypatch.setattr(
        enforcement_handler,
        "get_github_client",
        lambda: second_client,
    )
    second = await enforcement_handler.handle_day_close_enforcement(payload)
    assert second["status"] == "no_op_cutoff_exists"
    assert second["cutoffCommitSha"] == "first-sha"
    assert second["cutoffAt"] == cutoff_at.isoformat().replace("+00:00", "Z")
    assert second_client.calls == 0

    day_audit = await cs_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert day_audit is not None
    assert day_audit.cutoff_commit_sha == "first-sha"
