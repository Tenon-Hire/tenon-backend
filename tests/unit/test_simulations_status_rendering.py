from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.api.routers.simulations_routes import create as sim_create_route
from app.api.routers.simulations_routes import detail_render as sim_detail_render
from app.api.routers.simulations_routes import list_simulations as sim_list_route
from app.core.errors import ApiError


def _invalid_simulation() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=1,
        title="Invalid Sim",
        role="Backend Engineer",
        tech_stack="Python, FastAPI",
        seniority="Mid",
        focus="API quality",
        template_key="python-fastapi",
        scenario_template="default-5day-node-postgres",
        status="bad_status",
        generating_at=now,
        ready_for_review_at=now,
        activated_at=None,
        terminated_at=None,
        created_at=now,
    )


@pytest.mark.asyncio
async def test_create_route_rejects_invalid_status(monkeypatch):
    sim = _invalid_simulation()
    task = SimpleNamespace(id=9, day_index=1, type="code", title="Task")
    scenario_job = SimpleNamespace(id="job-123")

    monkeypatch.setattr(sim_create_route, "ensure_recruiter_or_none", lambda _u: None)

    async def _fake_create(*_args, **_kwargs):
        return sim, [task], scenario_job

    monkeypatch.setattr(
        sim_create_route.sim_service, "create_simulation_with_tasks", _fake_create
    )

    with pytest.raises(ApiError) as excinfo:
        await sim_create_route.create_simulation(
            payload=SimpleNamespace(),
            db=object(),
            user=SimpleNamespace(id=1, role="recruiter"),
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "SIMULATION_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}


@pytest.mark.asyncio
async def test_list_route_rejects_invalid_status(monkeypatch):
    sim = _invalid_simulation()

    monkeypatch.setattr(sim_list_route, "ensure_recruiter_or_none", lambda _u: None)

    async def _fake_list(*_args, **_kwargs):
        return [(sim, 0)]

    monkeypatch.setattr(sim_list_route.sim_service, "list_simulations", _fake_list)

    with pytest.raises(ApiError) as excinfo:
        await sim_list_route.list_simulations(
            db=object(), user=SimpleNamespace(id=1, role="recruiter")
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "SIMULATION_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}


def test_detail_render_rejects_invalid_status():
    sim = _invalid_simulation()
    with pytest.raises(ApiError) as excinfo:
        sim_detail_render.render_simulation_detail(
            sim, tasks=[], active_scenario_version=None
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "SIMULATION_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}
