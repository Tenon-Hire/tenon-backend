from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_update_simulation_without_notice_or_day_changes_skips_change_logs(
    monkeypatch,
):
    simulation = SimpleNamespace(
        id=45,
        ai_notice_version="notice-v1",
        ai_notice_text="text",
        ai_eval_enabled_by_day={"1": True, "2": False},
    )
    tasks = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = _DummyDB()

    async def _require_owned_with_tasks(_db, _simulation_id, _actor_user_id):
        return simulation, tasks

    calls = {"resolve": 0}

    def _resolve_fields(**kwargs):
        calls["resolve"] += 1
        if calls["resolve"] == 1:
            return ("notice-v1", "text", {"1": True, "2": False})
        return ("notice-v1", "text", {"1": True, "2": False})

    payload = SimpleNamespace(
        ai=SimpleNamespace(
            model_fields_set={"notice_version", "notice_text", "eval_enabled_by_day"},
            notice_version="notice-v1",
            notice_text="text",
            eval_enabled_by_day={"1": True, "2": False},
        )
    )

    monkeypatch.setattr(
        simulations_update,
        "require_owned_simulation_with_tasks",
        _require_owned_with_tasks,
    )
    monkeypatch.setattr(
        simulations_update, "resolve_simulation_ai_fields", _resolve_fields
    )

    updated_simulation, updated_tasks = await simulations_update.update_simulation(
        db,
        simulation_id=45,
        actor_user_id=99,
        payload=payload,
    )

    assert updated_simulation is simulation
    assert updated_tasks == tasks
    assert db.commits == 1
    assert db.refreshes == 3
