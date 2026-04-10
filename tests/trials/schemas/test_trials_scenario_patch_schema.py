from __future__ import annotations

import pytest
from pydantic import ValidationError

import app.trials.schemas.trials_schemas_trials_core_schema as sim_schemas


def test_patch_task_prompt_requires_title_and_description() -> None:
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchTaskPrompt.model_validate({"dayIndex": 2})


def test_patch_request_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate({})


def test_patch_request_validators_handle_explicit_nulls() -> None:
    parsed = sim_schemas.ScenarioVersionPatchRequest.model_validate(
        {"taskPrompts": None, "rubric": None, "notes": "ok"}
    )
    assert parsed.notes == "ok"
    assert parsed.taskPrompts is None
    assert parsed.rubric is None


def test_patch_request_rejects_legacy_notes_alias() -> None:
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate({"focusNotes": "legacy"})


def test_patch_request_rejects_non_array_task_prompts() -> None:
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate({"taskPrompts": {}})


def test_patch_request_rejects_non_object_rubric() -> None:
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate({"rubric": []})


def test_patch_request_rejects_oversized_task_prompts(monkeypatch) -> None:
    monkeypatch.setattr(sim_schemas, "MAX_SCENARIO_TASK_PROMPTS_BYTES", 5)
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate(
            {
                "taskPrompts": [
                    {
                        "dayIndex": 1,
                        "title": "Large title",
                        "description": "Large description",
                    }
                ]
            }
        )


def test_patch_request_rejects_oversized_rubric(monkeypatch) -> None:
    monkeypatch.setattr(sim_schemas, "MAX_SCENARIO_RUBRIC_BYTES", 5)
    with pytest.raises(ValidationError):
        sim_schemas.ScenarioVersionPatchRequest.model_validate(
            {"rubric": {"summary": "large"}}
        )
