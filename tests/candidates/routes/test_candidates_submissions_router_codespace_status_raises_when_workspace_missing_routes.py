from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_codespace_status_raises_when_workspace_missing(
    monkeypatch, async_session
):
    cs = _stub_cs()
    task = _stub_task()
    monkeypatch.setattr(
        candidate_submissions.submission_service,
        "load_task_or_404",
        _async_return(task),
    )
    monkeypatch.setattr(
        candidate_submissions.workspace_repo,
        "get_by_session_and_task",
        _async_return(None),
    )
    with pytest.raises(HTTPException) as excinfo:
        await candidate_submissions.codespace_status(
            task_id=task.id,
            candidate_session=cs,
            db=async_session,
        )
    assert excinfo.value.status_code == 404
