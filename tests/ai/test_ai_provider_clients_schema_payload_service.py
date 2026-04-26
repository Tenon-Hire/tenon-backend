from __future__ import annotations

from app.ai.ai_output_models import DayReviewerOutput, ScenarioGenerationOutput
from app.ai.ai_provider_clients_service import _schema_payload


def _walk_objects(schema_fragment):
    if isinstance(schema_fragment, dict):
        if schema_fragment.get("type") == "object":
            yield schema_fragment
        for value in schema_fragment.values():
            yield from _walk_objects(value)
    elif isinstance(schema_fragment, list):
        for value in schema_fragment:
            yield from _walk_objects(value)


def test_openai_compatible_schema_payload_is_strict_for_scenario_generation() -> None:
    schema = _schema_payload(ScenarioGenerationOutput)

    assert schema["title"] == "ScenarioGenerationOutput"
    assert "project_brief_md" in schema["required"]
    for object_schema in _walk_objects(schema):
        assert object_schema["additionalProperties"] is False
        assert set(object_schema.get("required", [])) == set(
            object_schema.get("properties", {}).keys()
        )


def test_anthropic_tool_schema_uses_current_day_reviewer_output_shape() -> None:
    schema = _schema_payload(DayReviewerOutput)

    assert schema["title"] == "DayReviewerOutput"
    assert "summary" in schema["required"]
    assert "rubricBreakdown" in schema["required"]
    assert "evidence" in schema["properties"]
    assert "fit_profile" not in str(schema).lower()
    assert "fit_score" not in str(schema).lower()
