from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_submit_task_enqueues_completion_notification_when_complete(
    monkeypatch,
):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=12, trial_id=44)
    task = SimpleNamespace(id=33, type="design")
    payload = SimpleNamespace(contentText="design text")
    created_submission = SimpleNamespace(id=501)
    captured: dict[str, object] = {}

    monkeypatch.setattr(submit_task_service, "apply_rate_limit", lambda *_args: None)

    async def _validate(*_args, **_kwargs):
        return task, {"kind": "design"}

    monkeypatch.setattr(
        submit_task_service,
        "validate_submission_flow",
        _validate,
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "is_code_task",
        lambda _task: False,
    )

    async def _create_submission(*_args, **_kwargs):
        return created_submission

    async def _progress_after_submission(*_args, **_kwargs):
        return (5, 5, True)

    async def _enqueue(_db, *, candidate_session_id, trial_id, commit):
        captured.update(
            {
                "candidate_session_id": candidate_session_id,
                "trial_id": trial_id,
                "commit": commit,
            }
        )
        return SimpleNamespace(id="job-1")

    monkeypatch.setattr(
        submit_task_service.submission_service, "create_submission", _create_submission
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "progress_after_submission",
        _progress_after_submission,
    )

    async def _get_draft(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        submit_task_service.task_drafts_repo,
        "get_by_session_and_task",
        _get_draft,
    )
    monkeypatch.setattr(
        submit_task_service.notification_service,
        "enqueue_candidate_completed_notification",
        _enqueue,
    )

    (
        _task_loaded,
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

    assert submission is created_submission
    assert (completed, total, is_complete) == (5, 5, True)
    assert captured == {
        "candidate_session_id": 12,
        "trial_id": 44,
        "commit": True,
    }
