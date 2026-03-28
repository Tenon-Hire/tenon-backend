from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_codespace_status_missing_repo_full_name(monkeypatch, async_session):
    cs = _stub_cs()
    task = _stub_task()
    workspace = _stub_workspace()
    workspace.repo_full_name = ""

    async def _return_task(*_a, **_k):
        return task

    async def _return_workspace_obj(*_a, **_kw):
        return workspace

    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _return_task,
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _return_workspace_obj,
    )

    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.codespace_status(
            task_id=task.id,
            candidate_session=cs,
            db=async_session,
        )
    assert excinfo.value.status_code == 409
