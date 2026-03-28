from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_simulation_routes_execute_service_calls(monkeypatch):
    user = SimpleNamespace(id=42)
    sim = SimpleNamespace(
        id=1,
        title="Sim",
        role="Backend",
        tech_stack="Python",
        seniority="Mid",
        focus="API",
        template_key="python-fastapi",
        scenario_template="default-5day-node-postgres",
        status="ready_for_review",
        generating_at=datetime.now(UTC),
        ready_for_review_at=datetime.now(UTC),
        activated_at=None,
        terminated_at=None,
        created_at=datetime.now(UTC),
    )
    task = SimpleNamespace(id=9, day_index=1, type="code", title="Task")
    scenario_job = SimpleNamespace(id="job-123")
    monkeypatch.setattr(sim_create_route, "ensure_recruiter_or_none", lambda _u: None)
    monkeypatch.setattr(sim_detail_route, "ensure_recruiter_or_none", lambda _u: None)
    monkeypatch.setattr(sim_list_route, "ensure_recruiter_or_none", lambda _u: None)

    async def _create_sim_with_tasks(*_a, **_k):
        return sim, [task], scenario_job

    async def _require_owned(*_a, **_k):
        return sim, [task]

    async def _list_sims(*_a, **_k):
        return [(sim, 2)]

    async def _get_active_scenario(*_a, **_k):
        return SimpleNamespace(id=10, version_index=1, status="ready", locked_at=None)

    monkeypatch.setattr(
        sim_create_route.sim_service,
        "create_simulation_with_tasks",
        _create_sim_with_tasks,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "require_owned_simulation_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "get_active_scenario_version",
        _get_active_scenario,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "render_simulation_detail",
        lambda _sim, _tasks, _active: {
            "id": _sim.id,
            "title": _sim.title,
            "tasks": _tasks,
        },
    )
    monkeypatch.setattr(sim_list_route.sim_service, "list_simulations", _list_sims)

    created = await sim_create_route.create_simulation(
        payload=SimpleNamespace(),
        db=object(),
        user=user,
    )
    detail = await sim_detail_route.get_simulation_detail(
        simulation_id=sim.id,
        db=object(),
        user=user,
    )
    listed = await sim_list_route.list_simulations(db=object(), user=user)
    assert created.id == sim.id
    assert detail["id"] == sim.id
    assert listed[0].numCandidates == 2
