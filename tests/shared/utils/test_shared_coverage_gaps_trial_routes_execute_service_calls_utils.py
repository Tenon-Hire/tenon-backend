from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_trial_routes_execute_service_calls(monkeypatch):
    user = SimpleNamespace(id=42)
    sim = SimpleNamespace(
        id=1,
        title="Sim",
        role="Backend",
        tech_stack="Python",
        seniority="Mid",
        focus="API",
        company_id=7,
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
    monkeypatch.setattr(
        sim_create_route, "ensure_talent_partner_or_none", lambda _u: None
    )
    monkeypatch.setattr(
        sim_detail_route, "ensure_talent_partner_or_none", lambda _u: None
    )
    monkeypatch.setattr(
        sim_list_route, "ensure_talent_partner_or_none", lambda _u: None
    )

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
        "create_trial_with_tasks",
        _create_sim_with_tasks,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "get_active_scenario_version",
        _get_active_scenario,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "render_trial_detail",
        lambda _sim, _tasks, _active, **_kwargs: {
            "id": _sim.id,
            "title": _sim.title,
            "tasks": _tasks,
        },
    )

    async def _load_pending(*_a, **_k):
        return None

    async def _resolve_bundle(*_a, **_k):
        return None

    monkeypatch.setattr(sim_detail_route, "_load_scenario_version", _load_pending)
    monkeypatch.setattr(
        sim_detail_route,
        "build_ai_policy_snapshot",
        lambda **_kwargs: {"promptPackVersion": "winoe-ai-pack-v1"},
    )
    monkeypatch.setattr(sim_detail_route, "_resolve_bundle_status", _resolve_bundle)
    monkeypatch.setattr(sim_list_route.sim_service, "list_trials", _list_sims)

    class _DbStub:
        async def scalar(self, *_args, **_kwargs):
            return None

    db = _DbStub()

    created = await sim_create_route.create_trial(
        payload=SimpleNamespace(),
        db=db,
        user=user,
    )
    detail = await sim_detail_route.get_trial_detail(
        trial_id=sim.id,
        db=db,
        user=user,
    )
    listed = await sim_list_route.list_trials(db=db, user=user)
    assert created.id == sim.id
    assert detail["id"] == sim.id
    assert listed[0].numCandidates == 2
