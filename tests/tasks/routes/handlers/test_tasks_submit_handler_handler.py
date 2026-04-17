from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import app.tasks.routes.tasks.handlers.tasks_routes_tasks_handlers_tasks_submit_handler as submit_task_handler
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    SubmissionCreateRequest,
)


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
    assert response.checkpointSha == "checkpoint-sha"
    assert response.finalSha is None


@pytest.mark.asyncio
async def test_handle_submit_task_normalizes_naive_cutoff_timestamp(monkeypatch):
    task = SimpleNamespace(id=22, day_index=2)
    submission = SimpleNamespace(
        id=99,
        submitted_at=datetime(2026, 3, 8, 15, 0, tzinfo=UTC),
        commit_sha="sha",
        checkpoint_sha=None,
        final_sha=None,
    )
    day_audit = SimpleNamespace(
        cutoff_commit_sha=None,
        cutoff_at=datetime(2026, 3, 8, 14, 0),
        eval_basis_ref=None,
    )

    async def _fake_submit_task(*_args, **_kwargs):
        return task, submission, 1, 5, False

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

    assert response.cutoffAt is not None
    assert response.cutoffAt.tzinfo is UTC


@pytest.mark.asyncio
async def test_handle_submit_task_uses_final_sha_for_day3(monkeypatch):
    task = SimpleNamespace(id=23, day_index=3)
    submission = SimpleNamespace(
        id=101,
        submitted_at=datetime(2026, 3, 8, 15, 0, tzinfo=UTC),
        commit_sha="mutable-head-sha",
        checkpoint_sha=None,
        final_sha="final-sha",
    )
    day_audit = SimpleNamespace(
        cutoff_commit_sha="cutoff-day3-sha",
        cutoff_at=datetime(2026, 3, 8, 18, 0, tzinfo=UTC),
        eval_basis_ref="refs/heads/main@cutoff",
    )

    async def _fake_submit_task(*_args, **_kwargs):
        return task, submission, 3, 5, False

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

    assert response.commitSha == "cutoff-day3-sha"
    assert response.cutoffCommitSha == "cutoff-day3-sha"
    assert response.checkpointSha is None
    assert response.finalSha == "final-sha"
    assert response.evalBasisRef == "refs/heads/main@cutoff"


@pytest.mark.asyncio
async def test_handle_submit_task_skips_day_audit_lookup_for_non_day2_day3(monkeypatch):
    task = SimpleNamespace(id=23, day_index=1)
    submission = SimpleNamespace(
        id=100,
        submitted_at=datetime(2026, 3, 8, 16, 0, tzinfo=UTC),
        commit_sha="commit-sha-day1",
        checkpoint_sha=None,
        final_sha=None,
    )

    async def _fake_submit_task(*_args, **_kwargs):
        return task, submission, 1, 5, False

    async def _fail_get_day_audit(*_args, **_kwargs):
        raise AssertionError("day audit lookup should not run for non-day2/day3 tasks")

    monkeypatch.setattr(submit_task_handler, "submit_task", _fake_submit_task)
    monkeypatch.setattr(
        submit_task_handler.cs_repo,
        "get_day_audit",
        _fail_get_day_audit,
    )

    response = await submit_task_handler.handle_submit_task(
        task_id=task.id,
        payload=SubmissionCreateRequest(contentText=None),
        candidate_session=SimpleNamespace(id=7),
        db=object(),
        github_client=object(),
        actions_runner=object(),
    )

    assert response.commitSha == "commit-sha-day1"
    assert response.cutoffCommitSha is None
    assert response.cutoffAt is None
