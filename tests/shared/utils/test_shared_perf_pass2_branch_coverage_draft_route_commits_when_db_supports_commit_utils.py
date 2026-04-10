from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_draft_route_commits_when_db_supports_commit(monkeypatch):
    task = SimpleNamespace(id=9, trial_id=2)
    draft = SimpleNamespace(updated_at=datetime.now(UTC))
    committed = {"count": 0}

    async def _snapshot(*_args, **_kwargs):
        return ([task], set(), task, 0, 1, False)

    async def _upsert(*_args, **_kwargs):
        return draft

    class _DB:
        async def commit(self):
            committed["count"] += 1

    monkeypatch.setattr(draft_route.cs_service, "progress_snapshot", _snapshot)
    monkeypatch.setattr(
        draft_route.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        draft_route,
        "validate_draft_payload_size",
        lambda **_kwargs: (1, 1),
    )
    monkeypatch.setattr(draft_route.task_drafts_repo, "upsert_draft", _upsert)

    response = await draft_route.put_task_draft_route(
        task_id=task.id,
        payload=TaskDraftUpsertRequest(contentText="x", contentJson=None),
        candidate_session=SimpleNamespace(id=1, trial_id=2),
        db=_DB(),
    )
    assert response.taskId == task.id
    assert committed["count"] == 1
