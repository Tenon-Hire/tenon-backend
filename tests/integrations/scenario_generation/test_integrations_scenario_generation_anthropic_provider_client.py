from __future__ import annotations

from app.ai.ai_output_models import (
    CodespaceSpec,
    ScenarioGenerationOutput,
    ScenarioRubric,
    ScenarioRubricDayWeights,
    ScenarioRubricDimension,
    ScenarioTaskPrompt,
)
from app.integrations.scenario_generation.anthropic_provider_client import (
    AnthropicScenarioGenerationProvider,
)
from app.integrations.scenario_generation.base_client import (
    ScenarioGenerationProviderRequest,
)


def _scenario_generation_output() -> ScenarioGenerationOutput:
    return ScenarioGenerationOutput(
        storyline_md="Short scenario",
        task_prompts_json=[
            ScenarioTaskPrompt(
                dayIndex=day_index,
                title=f"Day {day_index}",
                description=f"Do the work for day {day_index}.",
            )
            for day_index in range(1, 6)
        ],
        rubric_json=ScenarioRubric(
            summary="Short rubric",
            dayWeights=ScenarioRubricDayWeights(
                day1=10, day2=20, day3=30, day4=20, day5=20
            ),
            dimensions=[
                ScenarioRubricDimension(
                    name="Planning",
                    weight=50,
                    description="Plans well.",
                ),
                ScenarioRubricDimension(
                    name="Execution",
                    weight=50,
                    description="Delivers well.",
                ),
            ],
        ),
        codespace_spec_json=CodespaceSpec(
            summary="Build the feature.",
            candidate_goal="Ship the requested backend changes.",
            acceptance_criteria=["It works.", "It is tested."],
            target_files=["app/example.py"],
            repo_adjustments=["Add endpoint"],
            test_focus=["happy path"],
            test_command="poetry run pytest tests/example",
        ),
    )


def test_anthropic_scenario_generation_provider_uses_larger_output_budget(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def _fake_call_anthropic_json(**kwargs):
        calls.append(kwargs)
        return _scenario_generation_output()

    monkeypatch.setattr(
        "app.integrations.scenario_generation.anthropic_provider_client.call_anthropic_json",
        _fake_call_anthropic_json,
    )
    monkeypatch.setattr(
        "app.integrations.scenario_generation.anthropic_provider_client.settings.ANTHROPIC_API_KEY",
        "anthropic-test-key",
    )

    provider = AnthropicScenarioGenerationProvider()
    response = provider.generate_scenario(
        request=ScenarioGenerationProviderRequest(
            system_prompt="system",
            user_prompt="user",
            model="claude-opus-4-6",
        )
    )

    assert len(calls) == 1
    assert calls[0]["max_tokens"] == 6_144
    assert response.model_name == "claude-opus-4-6"
    assert response.model_version == "claude-opus-4-6"
    assert response.result.storyline_md == "Short scenario"
