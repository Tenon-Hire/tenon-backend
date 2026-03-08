from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import app.api.routers.tasks.handlers.submit_task as submit_task_handler
from app.domains.submissions.schemas import SubmissionCreateRequest


@pytest.mark.asyncio
async def test_handle_submit_task_uses_pinned_cutoff_commit_basis(monkeypatch):
    task = SimpleNamespace(id=22, day_index=2)
    submission = SimpleNamespace(
        id=99,
        submitted_at=datetime(2026, 3, 8, 15, 0, tzinfo=UTC),
        commit_sha="mutable-head-sha",
        checkpoint_sha="checkpoint-sha",
        final_sha=None,
    )
    day_audit = SimpleNamespace(
        cutoff_commit_sha="pinned-cutoff-sha",
        cutoff_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC),
        eval_basis_ref="refs/heads/main@cutoff",
    )

    async def _fake_submit_task(*_args, **_kwargs):
        return task, submission, 2, 5, False

    async def _fake_get_day_audit(*_args, **_kwargs):
        return day_audit

    monkeypatch.setattr(submit_task_handler, "submit_task", _fake_submit_task)
    monkeypatch.setattr(
        submit_task_handler.cs_repo,
        "get_day_audit",
        _fake_get_day_audit,
    )

    response = await submit_task_handler.handle_submit_task(
        task_id=task.id,
        payload=SubmissionCreateRequest(contentText=None),
        candidate_session=SimpleNamespace(id=7),
        db=object(),
        github_client=object(),
        actions_runner=object(),
    )

    assert response.commitSha == "pinned-cutoff-sha"
    assert response.cutoffCommitSha == "pinned-cutoff-sha"
    assert response.commitSha == response.cutoffCommitSha
    assert response.commitSha != submission.commit_sha
    assert response.evalBasisRef == "refs/heads/main@cutoff"
