from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.trials.routes.trials_routes import scenario
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioVersionPatchRequest,
)


@pytest.mark.asyncio
async def test_approve_scenario_route_promotes_pending(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_talent_partner_or_none", lambda _u: None)

    async def fake_approve(db, trial_id, scenario_version_id, actor_user_id):
        assert trial_id == 8
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
        trial_id=8,
        scenario_version_id=22,
        db=object(),
        user=SimpleNamespace(id=9, role="talent_partner"),
    )
    assert response.trialId == 8
    assert response.status == "active_inviting"
    assert response.activeScenarioVersionId == 22
    assert response.pendingScenarioVersionId is None
    assert response.scenario.id == 22


@pytest.mark.asyncio
async def test_patch_scenario_version_route_normalizes_fields(monkeypatch):
    monkeypatch.setattr(scenario, "ensure_talent_partner_or_none", lambda _u: None)
    captured = {}

    async def fake_patch(db, trial_id, scenario_version_id, actor_user_id, updates):
        captured["updates"] = updates
        assert trial_id == 8
        assert scenario_version_id == 22
        assert actor_user_id == 9
        return SimpleNamespace(id=22, status="ready")

    monkeypatch.setattr(scenario.sim_service, "patch_scenario_version", fake_patch)
    payload = ScenarioVersionPatchRequest(
        storylineMd="Story v2",
        taskPrompts=[
            {"dayIndex": 2, "title": "Updated Task", "description": "Updated wording"}
        ],
        rubric={"dayWeights": {"2": 30}},
        notes="Keep candidate constraints explicit",
    )
    response = await scenario.patch_scenario_version(
        trial_id=8,
        scenario_version_id=22,
        payload=payload,
        db=object(),
        user=SimpleNamespace(id=9, role="talent_partner"),
    )
    assert captured["updates"] == {
        "storyline_md": "Story v2",
        "task_prompts_json": [
            {"dayIndex": 2, "title": "Updated Task", "description": "Updated wording"}
        ],
        "rubric_json": {"dayWeights": {"2": 30}},
        "focus_notes": "Keep candidate constraints explicit",
    }
    assert response.scenarioVersionId == 22
    assert response.status == "ready"
