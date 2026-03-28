from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_get_run_result_success_direct(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    result = ActionsRunResult(
        status="failed",
        run_id=10,
        conclusion="failure",
        passed=None,
        failed=None,
        total=None,
        stdout=None,
        stderr=None,
        head_sha="sha",
        html_url=None,
        raw=None,
    )

    _return_cs = _async_return(cs)
    _return_task = _async_return(task)
    _return_workspace_obj = _async_return(workspace)
    _record_result = _async_return(workspace)

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
        _return_workspace_obj,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "record_run_result",
        _record_result,
    )

    class Runner:
        async def fetch_run_result(self, **_kwargs):
            return result

    resp = await candidate_submissions.get_run_result(
        task_id=task.id,
        run_id=result.run_id,
        db=async_session,
        actions_runner=Runner(),
        candidate_session=cs,
    )
    assert resp.runId == 10
    assert resp.status == "failed"
