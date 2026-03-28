from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.simulations.routes.simulations_routes import (
    simulations_routes_simulations_routes_simulations_routes_update_routes as update_routes,
)


@pytest.mark.asyncio
async def test_update_simulation_route_renders_detail_response(monkeypatch):
    captured: dict[str, object] = {}
    simulation = SimpleNamespace(id=15)
    tasks = [SimpleNamespace(id=1)]
    active_scenario = SimpleNamespace(id=7)
    rendered = {"id": 15, "scenarioVersionId": 7}

    monkeypatch.setattr(update_routes, "ensure_recruiter_or_none", lambda _user: None)

    async def _fake_update_simulation(
        _db,
        *,
        simulation_id: int,
        actor_user_id: int,
        payload,
    ):
        captured["simulation_id"] = simulation_id
        captured["actor_user_id"] = actor_user_id
        captured["payload"] = payload
        return simulation, tasks

    async def _fake_get_active_scenario_version(_db, simulation_id: int):
        captured["active_lookup_simulation_id"] = simulation_id
        return active_scenario

    def _fake_render(sim, task_rows, scenario):
        captured["render_args"] = (sim, task_rows, scenario)
        return rendered

    monkeypatch.setattr(
        update_routes.sim_service, "update_simulation", _fake_update_simulation
    )
    monkeypatch.setattr(
        update_routes.sim_service,
        "get_active_scenario_version",
        _fake_get_active_scenario_version,
    )
    monkeypatch.setattr(update_routes, "render_simulation_detail", _fake_render)

    result = await update_routes.update_simulation(
        simulation_id=15,
        payload=SimpleNamespace(title="Updated"),
        db=object(),
        user=SimpleNamespace(id=33),
    )

    assert result == rendered
    assert captured["simulation_id"] == 15
    assert captured["actor_user_id"] == 33
    assert captured["active_lookup_simulation_id"] == 15
    assert captured["render_args"] == (simulation, tasks, active_scenario)
