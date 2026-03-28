from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_load_task_or_404_branches(monkeypatch, async_session):
    class DummyTask:
        id = 1

    async def _return_task(db, task_id):
        return DummyTask()

    async def _return_none(db, task_id):
        return None

    monkeypatch.setattr(svc.tasks_repo, "get_by_id", _return_task)
    assert await svc.load_task_or_404(async_session, 1) is not None

    monkeypatch.setattr(svc.tasks_repo, "get_by_id", _return_none)
    with pytest.raises(HTTPException):
        await svc.load_task_or_404(async_session, 99)
