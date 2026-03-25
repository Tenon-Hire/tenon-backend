from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_run_task_tests_success_direct(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    result = ActionsRunResult(
        status="passed",
        run_id=9,
        conclusion="success",
        passed=1,
        failed=0,
        total=1,
        stdout="ok",
        stderr=None,
        head_sha="sha",
        html_url="https://example.com/run/9",
        raw=None,
    )

    async def _return_cs(*_a, **_k):
        return cs

    async def _return_task(*_a, **_k):
        return task

    async def _return_workspace(*_a, **_k):
        return workspace

    monkeypatch.setattr(
        candidate_submissions, "_rate_limit_or_429", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _return_task,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_task_belongs",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_run_allowed",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _return_workspace,
    )

    async def _return_result(**_kw):
        return result

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "run_actions_tests",
        _return_result,
    )

    async def _record_result(*_a, **_k):
        return workspace

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "record_run_result",
        _record_result,
    )

    resp = await candidate_submissions.run_task_tests(
        task_id=task.id,
        payload=RunTestsRequest(branch=None, workflowInputs=None),
        db=async_session,
        actions_runner=object(),
        candidate_session=cs,
    )
    assert resp.runId == 9
    assert resp.status == "passed"
