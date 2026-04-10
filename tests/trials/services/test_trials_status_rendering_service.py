from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.routes.trials_routes import create as sim_create_route
from app.trials.routes.trials_routes import (
    trials_routes_trials_routes_trials_routes_detail_render_routes as sim_detail_render,
)
from app.trials.routes.trials_routes import (
    trials_routes_trials_routes_trials_routes_list_trials_routes as sim_list_route,
)


def _invalid_trial() -> SimpleNamespace:
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
    sim = _invalid_trial()
    task = SimpleNamespace(id=9, day_index=1, type="code", title="Task")
    scenario_job = SimpleNamespace(id="job-123")

    monkeypatch.setattr(
        sim_create_route, "ensure_talent_partner_or_none", lambda _u: None
    )

    async def _fake_create(*_args, **_kwargs):
        return sim, [task], scenario_job

    monkeypatch.setattr(
        sim_create_route.sim_service, "create_trial_with_tasks", _fake_create
    )

    with pytest.raises(ApiError) as excinfo:
        await sim_create_route.create_trial(
            payload=SimpleNamespace(),
            db=object(),
            user=SimpleNamespace(id=1, role="talent_partner"),
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "TRIAL_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}


@pytest.mark.asyncio
async def test_list_route_rejects_invalid_status(monkeypatch):
    sim = _invalid_trial()

    monkeypatch.setattr(
        sim_list_route, "ensure_talent_partner_or_none", lambda _u: None
    )

    async def _fake_list(*_args, **_kwargs):
        return [(sim, 0)]

    monkeypatch.setattr(sim_list_route.sim_service, "list_trials", _fake_list)

    with pytest.raises(ApiError) as excinfo:
        await sim_list_route.list_trials(
            db=object(), user=SimpleNamespace(id=1, role="talent_partner")
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "TRIAL_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}


def test_detail_render_rejects_invalid_status():
    sim = _invalid_trial()
    with pytest.raises(ApiError) as excinfo:
        sim_detail_render.render_trial_detail(
            sim, tasks=[], active_scenario_version=None
        )
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "TRIAL_STATUS_INVALID"
    assert excinfo.value.details == {"status": "bad_status"}
