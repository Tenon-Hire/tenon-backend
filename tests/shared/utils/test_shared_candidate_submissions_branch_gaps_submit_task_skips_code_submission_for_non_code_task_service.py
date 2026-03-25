from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_submit_task_skips_code_submission_for_non_code_task(monkeypatch):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=12)
    task = SimpleNamespace(id=33, type="design")
    payload = SimpleNamespace(contentText="design text")
    created_submission = SimpleNamespace(id=501)

    calls = {"rate_limit": 0, "run_code_submission": 0}

    def _apply_rate_limit(_session_id, _action):
        calls["rate_limit"] += 1

    async def _validate(_db, _candidate_session, _task_id, _payload):
        return task, {"kind": "design"}

    async def _run_code_submission(**_kwargs):
        calls["run_code_submission"] += 1
        return "should-not-run"

    async def _create_submission(*_args, **_kwargs):
        return created_submission

    async def _progress_after_submission(*_args, **_kwargs):
        return (1, 5, False)

    monkeypatch.setattr(submit_task_service, "apply_rate_limit", _apply_rate_limit)
    monkeypatch.setattr(submit_task_service, "validate_submission_flow", _validate)
    monkeypatch.setattr(
        submit_task_service, "run_code_submission", _run_code_submission
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "is_code_task",
        lambda _task: False,
    )
    monkeypatch.setattr(
        submit_task_service.submission_service, "create_submission", _create_submission
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "progress_after_submission",
        _progress_after_submission,
    )

    (
        task_loaded,
        submission,
        completed,
        total,
        is_complete,
    ) = await submit_task_service.submit_task(
        db,
        candidate_session=candidate_session,
        task_id=33,
        payload=payload,
        github_client=SimpleNamespace(),
        actions_runner=SimpleNamespace(),
    )

    assert task_loaded is task
    assert submission is created_submission
    assert (completed, total, is_complete) == (1, 5, False)
    assert calls["rate_limit"] == 1
    assert calls["run_code_submission"] == 0
