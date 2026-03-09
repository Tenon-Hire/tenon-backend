from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute

from app.api.routers.simulations_routes import scenario
from app.domains.simulations.schemas import ScenarioActiveUpdateRequest
from app.main import app


def _fake_request():
    return type(
        "Req",
        (),
        {"headers": {}, "client": type("c", (), {"host": "127.0.0.1"})()},
    )()


@pytest.mark.asyncio
async def test_regenerate_scenario_route_returns_scenario_summary(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_recruiter_or_none", lambda _u: None)
    calls = {"limit": 0}

    async def fake_regenerate(db, simulation_id, actor_user_id):
        assert simulation_id == 42
        assert actor_user_id == 7
        return (
            SimpleNamespace(id=42),
            SimpleNamespace(
                id=10, version_index=2, status="generating", locked_at=None
            ),
            SimpleNamespace(id="job-123"),
        )

    monkeypatch.setattr(
        scenario.sim_service,
        "request_scenario_regeneration",
        fake_regenerate,
    )
    monkeypatch.setattr(
        scenario,
        "enforce_scenario_regenerate_limit",
        lambda _req, _user_id: calls.__setitem__("limit", calls["limit"] + 1),
    )

    response = await scenario.regenerate_scenario_version(
        simulation_id=42,
        request=_fake_request(),
        db=object(),
        user=SimpleNamespace(id=7, role="recruiter"),
    )

    assert calls["limit"] == 1
    assert response.scenarioVersionId == 10
    assert response.jobId == "job-123"
    assert response.status == "generating"


@pytest.mark.asyncio
async def test_update_active_scenario_route_normalizes_fields(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_recruiter_or_none", lambda _u: None)
    captured = {}

    async def fake_update(db, simulation_id, actor_user_id, updates):
        captured["updates"] = updates
        return SimpleNamespace(
            id=15,
            version_index=3,
            status="draft",
            locked_at=None,
        )

    monkeypatch.setattr(
        scenario.sim_service,
        "update_active_scenario_version",
        fake_update,
    )

    payload = ScenarioActiveUpdateRequest(
        storylineMd="Story",
        taskPromptsJson=[{"dayIndex": 1, "title": "Task"}],
        rubricJson={"summary": "rubric"},
        focusNotes="Focus note",
        status="draft",
    )
    response = await scenario.update_active_scenario_version(
        simulation_id=8,
        payload=payload,
        db=object(),
        user=SimpleNamespace(id=9, role="recruiter"),
    )

    assert captured["updates"] == {
        "storyline_md": "Story",
        "task_prompts_json": [{"dayIndex": 1, "title": "Task"}],
        "rubric_json": {"summary": "rubric"},
        "focus_notes": "Focus note",
        "status": "draft",
    }
    assert response.simulationId == 8
    assert response.scenario.id == 15
    assert response.scenario.versionIndex == 3
    assert response.scenario.status == "draft"


@pytest.mark.asyncio
async def test_approve_scenario_route_promotes_pending(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_recruiter_or_none", lambda _u: None)

    async def fake_approve(
        db, simulation_id, scenario_version_id, actor_user_id
    ):  # pragma: no cover - thin contract test
        assert simulation_id == 8
        assert scenario_version_id == 22
        assert actor_user_id == 9
        return (
            SimpleNamespace(
                id=8,
                status="active_inviting",
                active_scenario_version_id=22,
                pending_scenario_version_id=None,
            ),
            SimpleNamespace(id=22, version_index=2, status="ready", locked_at=None),
        )

    monkeypatch.setattr(scenario.sim_service, "approve_scenario_version", fake_approve)

    response = await scenario.approve_scenario_version(
        simulation_id=8,
        scenario_version_id=22,
        db=object(),
        user=SimpleNamespace(id=9, role="recruiter"),
    )
    assert response.simulationId == 8
    assert response.status == "active_inviting"
    assert response.activeScenarioVersionId == 22
    assert response.pendingScenarioVersionId is None
    assert response.scenario.id == 22


def test_scenario_routes_are_registered_once():
    expected = [
        ("POST", "/api/simulations/{simulation_id}/scenario/regenerate"),
        (
            "POST",
            "/api/simulations/{simulation_id}/scenario/{scenario_version_id}/approve",
        ),
        ("PATCH", "/api/simulations/{simulation_id}/scenario/active"),
    ]

    for method, path in expected:
        matches = [
            route
            for route in app.routes
            if isinstance(route, APIRoute)
            and route.path == path
            and method in (route.methods or set())
        ]
        assert len(matches) == 1
