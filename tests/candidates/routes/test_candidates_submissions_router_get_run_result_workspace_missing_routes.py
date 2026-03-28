from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_get_run_result_workspace_missing(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _async_return(task),
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "ensure_task_belongs",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "validate_run_allowed",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _async_return(None),
    )
    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.get_run_result(
            task_id=task.id,
            run_id=1,
            db=async_session,
            actions_runner=object(),
            candidate_session=cs,
        )
    assert excinfo.value.status_code == 400
