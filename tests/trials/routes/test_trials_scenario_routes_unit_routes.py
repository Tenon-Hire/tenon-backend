from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.trials.routes.trials_routes import scenario
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioActiveUpdateRequest,
)


def _fake_request():
    return type(
        "Req", (), {"headers": {}, "client": type("c", (), {"host": "127.0.0.1"})()}
    )()


@pytest.mark.asyncio
async def test_regenerate_scenario_route_returns_scenario_summary(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_talent_partner_or_none", lambda _u: None)
    calls = {"limit": 0}

    async def fake_regenerate(db, trial_id, actor_user_id):
        assert trial_id == 42
        assert actor_user_id == 7
        return (
            SimpleNamespace(id=42),
            SimpleNamespace(
                id=10, version_index=2, status="generating", locked_at=None
            ),
            SimpleNamespace(id="job-123"),
        )

    monkeypatch.setattr(
        scenario.sim_service, "request_scenario_regeneration", fake_regenerate
    )
    monkeypatch.setattr(
        scenario,
        "enforce_scenario_regenerate_limit",
        lambda _req, _user_id: calls.__setitem__("limit", calls["limit"] + 1),
    )
    response = await scenario.regenerate_scenario_version(
        trial_id=42,
        request=_fake_request(),
        db=object(),
        user=SimpleNamespace(id=7, role="talent_partner"),
    )
    assert calls["limit"] == 1
    assert response.scenarioVersionId == 10
    assert response.jobId == "job-123"
    assert response.status == "generating"


@pytest.mark.asyncio
async def test_update_active_scenario_route_normalizes_fields(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_talent_partner_or_none", lambda _u: None)
    captured = {}

    async def fake_update(db, trial_id, actor_user_id, updates):
        captured["updates"] = updates
        return SimpleNamespace(id=15, version_index=3, status="draft", locked_at=None)

    monkeypatch.setattr(
        scenario.sim_service, "update_active_scenario_version", fake_update
    )
    payload = ScenarioActiveUpdateRequest(
        storylineMd="Story",
        taskPromptsJson=[{"dayIndex": 1, "title": "Task"}],
        rubricJson={"summary": "rubric"},
        focusNotes="Focus note",
        status="draft",
    )
    response = await scenario.update_active_scenario_version(
        trial_id=8,
        payload=payload,
        db=object(),
        user=SimpleNamespace(id=9, role="talent_partner"),
    )
    assert captured["updates"] == {
        "storyline_md": "Story",
        "task_prompts_json": [{"dayIndex": 1, "title": "Task"}],
        "rubric_json": {"summary": "rubric"},
        "focus_notes": "Focus note",
        "status": "draft",
    }
    assert response.trialId == 8
    assert response.scenario.id == 15
    assert response.scenario.versionIndex == 3
    assert response.scenario.status == "draft"
