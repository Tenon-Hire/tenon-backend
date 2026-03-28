from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_invite_list_reuses_cached_tasks_per_simulation(monkeypatch):
    sessions = [
        SimpleNamespace(id=1, simulation_id=22),
        SimpleNamespace(id=2, simulation_id=22),
    ]
    principal = SimpleNamespace(email="candidate@example.com")
    calls = {"tasks_for_simulation": 0}

    async def _list_for_email(_db, _email, include_terminated=False):
        assert include_terminated is False
        return sessions

    async def _last_submission_map(_db, session_ids):
        assert session_ids == [1, 2]
        return {}

    async def _tasks_for_simulation(_db, simulation_id):
        calls["tasks_for_simulation"] += 1
        assert simulation_id == 22
        return [SimpleNamespace(id=101)]

    async def _build_invite_item(
        _db,
        cs,
        *,
        now,
        last_submitted_map,
        tasks_loader,
    ):
        assert isinstance(now, datetime)
        assert last_submitted_map == {}
        tasks = await tasks_loader(cs.simulation_id)
        return {"sessionId": cs.id, "taskCount": len(tasks)}

    monkeypatch.setattr(invites_service.cs_repo, "list_for_email", _list_for_email)
    monkeypatch.setattr(
        invites_service.cs_repo, "tasks_for_simulation", _tasks_for_simulation
    )
    monkeypatch.setattr(invites_service, "last_submission_map", _last_submission_map)
    monkeypatch.setattr(invites_service, "build_invite_item", _build_invite_item)

    items = await invites_service.invite_list_for_principal(
        _DummyDB(),
        principal,
    )

    assert len(items) == 2
    assert calls["tasks_for_simulation"] == 1
