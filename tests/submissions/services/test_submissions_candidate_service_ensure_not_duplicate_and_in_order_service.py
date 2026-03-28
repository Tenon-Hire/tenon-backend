from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_not_duplicate_and_in_order(monkeypatch):
    async def _dup_true(db, cs_id, task_id):
        return True

    async def _dup_false(db, cs_id, task_id):
        return False

    monkeypatch.setattr(svc.submissions_repo, "find_duplicate", _dup_false)
    # Should not raise
    svc.ensure_in_order(SimpleNamespace(id=1), target_task_id=1)

    monkeypatch.setattr(svc.submissions_repo, "find_duplicate", _dup_true)
    with pytest.raises(HTTPException):
        await svc.ensure_not_duplicate(None, 1, 1)

    with pytest.raises(HTTPException):
        svc.ensure_in_order(None, target_task_id=1)

    with pytest.raises(HTTPException):
        svc.ensure_in_order(SimpleNamespace(id=2), target_task_id=1)
