from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import AIPolicySnapshotError, build_ai_policy_snapshot
from app.ai.ai_output_models import (
    ScenarioGenerationOutput,
    ScenarioRubric,
    ScenarioRubricDimension,
    ScenarioTaskPrompt,
)
from app.integrations.scenario_generation.base_client import (
    ScenarioGenerationProviderError,
    ScenarioGenerationProviderRequest,
    ScenarioGenerationProviderResponse,
)
from app.trials.services import scenario_generation


def _snapshot():
    trial = SimpleNamespace(
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    return build_ai_policy_snapshot(trial=trial)


def test_deterministic_template_generation_is_stable_for_same_inputs() -> None:
    first = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python, FastAPI, PostgreSQL",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )
    second = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python, FastAPI, PostgreSQL",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert first == second
    assert len(first.task_prompts_json) == 5
    assert first.project_brief_md.startswith("# Project Brief")
    assert (
        first.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_choose_generation_source_fails_closed_without_llm_keys() -> None:
    with pytest.raises(RuntimeError, match="scenario_generation_provider_unavailable"):
        scenario_generation.choose_generation_source(
            demo_mode_enabled=False,
            llm_available=False,
        )


def test_choose_generation_source_prefers_fallback_in_demo_mode() -> None:
    source = scenario_generation.choose_generation_source(
        demo_mode_enabled=True,
        llm_available=True,
    )
    assert source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK


def test_generate_scenario_payload_uses_fallback_when_runtime_selects_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        scenario_generation,
        "choose_generation_source",
        lambda **_kwargs: scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK,
    )
    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_generate_scenario_payload_uses_fallback_in_demo_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_generation,
        "choose_generation_source",
        lambda **_kwargs: scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK,
    )
    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_generate_scenario_payload_fails_closed_when_llm_generation_errors(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        scenario_generation,
        "choose_generation_source",
        lambda **_kwargs: scenario_generation.SCENARIO_SOURCE_LLM,
    )

    def _explode(
        *,
        role: str,
        template_key: str,
        scenario_template=None,
        focus=None,
        company_context=None,
        company_prompt_overrides_json=None,
        trial_prompt_overrides_json=None,
        preferred_language_framework=None,
        ai_policy_snapshot_json=None,
    ):
        raise RuntimeError("llm exploded")

    monkeypatch.setattr(scenario_generation, "_generate_with_llm", _explode)
    with pytest.raises(RuntimeError, match="llm exploded"):
        scenario_generation.generate_scenario_payload(
            role="Backend Engineer",
            tech_stack="Python",
            template_key="python-fastapi",
            ai_policy_snapshot_json=_snapshot(),
        )


def test_generate_scenario_payload_raises_on_retryable_provider_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        scenario_generation,
        "choose_generation_source",
        lambda **_kwargs: scenario_generation.SCENARIO_SOURCE_LLM,
    )

    def _rate_limited(**_kwargs):
        raise RuntimeError("openai_request_failed:RateLimitError")

    monkeypatch.setattr(scenario_generation, "_generate_with_llm", _rate_limited)

    with pytest.raises(RuntimeError, match="openai_request_failed:RateLimitError"):
        scenario_generation.generate_scenario_payload(
            role="Backend Engineer",
            tech_stack="Python",
            template_key="python-fastapi",
            ai_policy_snapshot_json=_snapshot(),
        )


def test_generate_scenario_payload_fails_closed_when_source_selection_fails(
    monkeypatch,
) -> None:
    def _raise_source(*_args, **_kwargs):
        raise RuntimeError("scenario_generation_provider_unavailable")

    monkeypatch.setattr(scenario_generation, "choose_generation_source", _raise_source)
    with pytest.raises(RuntimeError, match="scenario_generation_provider_unavailable"):
        scenario_generation.generate_scenario_payload(
            role="Backend Engineer",
            tech_stack="Python",
            template_key="python-fastapi",
            ai_policy_snapshot_json=_snapshot(),
        )


def test_project_brief_stays_open_ended_for_context_changes() -> None:
    payload = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="missing-template",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert payload.project_brief_md.startswith("# Project Brief")
    assert "codespace" not in payload.project_brief_md.lower()
    assert "python" not in payload.project_brief_md.lower()
    assert "template" not in payload.project_brief_md.lower()


def test_deterministic_template_generation_uses_demo_and_reflection_language() -> None:
    payload = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )
    day4 = next(
        prompt for prompt in payload.task_prompts_json if prompt["dayIndex"] == 4
    )
    day5 = next(
        prompt for prompt in payload.task_prompts_json if prompt["dayIndex"] == 5
    )

    day3 = next(
        prompt for prompt in payload.task_prompts_json if prompt["dayIndex"] == 3
    )
    assert "demo presentation" in day4["description"].lower()
    assert "reflection essay" in day5["description"].lower()
    assert "implementation wrap-up" in day3["title"].lower()
    assert "wrap-up" in day3["description"].lower()
    assert "debug" not in day3["description"].lower()
    assert "wrap-up" in payload.rubric_json["summary"].lower()
    assert any(
        dimension["name"] == "Communication and presentation"
        for dimension in payload.rubric_json["dimensions"]
    )
    assert any(
        dimension["name"] == "Implementation completeness and handoff readiness"
        for dimension in payload.rubric_json["dimensions"]
    )
    assert all(
        "debug" not in dimension["name"].lower()
        and "debug" not in dimension["description"].lower()
        for dimension in payload.rubric_json["dimensions"]
    )


def test_generate_with_llm_placeholder_raises(monkeypatch) -> None:
    class _FailingProvider:
        def generate_scenario(self, *, request):
            raise ScenarioGenerationProviderError("missing_openai_api_key")

    monkeypatch.setattr(
        scenario_generation,
        "get_scenario_generation_provider",
        lambda _provider: _FailingProvider(),
    )

    with pytest.raises(RuntimeError, match="missing_openai_api_key"):
        scenario_generation._generate_with_llm(
            role="Backend Engineer",
            template_key="python-fastapi",
            ai_policy_snapshot_json=_snapshot(),
        )


def test_is_retryable_scenario_generation_error_detects_blank_and_marker() -> None:
    assert not scenario_generation._is_retryable_scenario_generation_error(
        Exception("")
    )
    assert not scenario_generation._is_retryable_scenario_generation_error(
        Exception("temporary provider issue")
    )
    assert scenario_generation._is_retryable_scenario_generation_error(
        Exception("Rate limit exceeded")
    )


def test_generate_with_llm_success_includes_override_context(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _build_prompt(*, snapshot_json, agent_key, run_context_md):
        captured["snapshot_json"] = snapshot_json
        captured["agent_key"] = agent_key
        captured["run_context_md"] = run_context_md
        return "system prompt", "rubric guidance"

    def _require_agent_runtime(snapshot_json, agent_key):
        captured["runtime_snapshot_json"] = snapshot_json
        captured["runtime_agent_key"] = agent_key
        return {"provider": "anthropic", "model": "claude-opus-4.6"}

    def _require_agent_policy_snapshot(snapshot_json, agent_key):
        captured["policy_snapshot_json"] = snapshot_json
        captured["policy_agent_key"] = agent_key
        return {"promptVersion": "v9", "rubricVersion": "r9"}

    class _Provider:
        def generate_scenario(
            self, *, request: ScenarioGenerationProviderRequest
        ) -> ScenarioGenerationProviderResponse:
            captured["request"] = request
            return ScenarioGenerationProviderResponse(
                result=ScenarioGenerationOutput(
                    storyline_md="A custom storyline with a realistic demo path.",
                    task_prompts_json=[
                        ScenarioTaskPrompt(
                            dayIndex=1,
                            title="Plan the stack",
                            description="Define the initial implementation plan.",
                        ),
                        ScenarioTaskPrompt(
                            dayIndex=2,
                            title="Build the core",
                            description="Implement the core backend workflow.",
                        ),
                        ScenarioTaskPrompt(
                            dayIndex=3,
                            title="Integrate the UI",
                            description="Wire the implementation into the UI.",
                        ),
                        ScenarioTaskPrompt(
                            dayIndex=4,
                            title="Polish for demo",
                            description="Prepare the demo narrative and edge cases.",
                        ),
                        ScenarioTaskPrompt(
                            dayIndex=5,
                            title="Reflect and ship",
                            description="Finalize the submission and document tradeoffs.",
                        ),
                    ],
                    rubric_json=ScenarioRubric(
                        summary="Generated rubric for the scenario.",
                        dayWeights={
                            "1": 10,
                            "2": 20,
                            "3": 25,
                            "4": 20,
                            "5": 25,
                        },
                        dimensions=[
                            ScenarioRubricDimension(
                                name="Scope",
                                weight=40,
                                description="Evaluates whether the work is well scoped.",
                            ),
                            ScenarioRubricDimension(
                                name="Delivery",
                                weight=60,
                                description="Evaluates implementation quality and finish.",
                            ),
                        ],
                    ),
                    project_brief_md="# Project Brief\n\n## Business Context\n\nA custom scenario requiring full-stack work.\n",
                ),
                model_name="claude-opus-4.6",
                model_version="2024-11-15",
            )

    monkeypatch.setattr(
        scenario_generation,
        "build_required_snapshot_prompt",
        _build_prompt,
    )
    monkeypatch.setattr(
        scenario_generation,
        "require_agent_runtime",
        _require_agent_runtime,
    )
    monkeypatch.setattr(
        scenario_generation,
        "require_agent_policy_snapshot",
        _require_agent_policy_snapshot,
    )
    monkeypatch.setattr(
        scenario_generation,
        "get_scenario_generation_provider",
        lambda _provider: _Provider(),
    )

    payload = scenario_generation._generate_with_llm(
        role="Backend Engineer",
        template_key="python-fastapi",
        focus="Emphasize production realism.",
        company_context={
            "domain": "payments",
            "productArea": "billing",
            "preferred_language_framework": "TypeScript/Node",
        },
        company_prompt_overrides_json={"tone": "pragmatic"},
        trial_prompt_overrides_json={"scope": "end-to-end"},
        ai_policy_snapshot_json=_snapshot(),
    )

    assert payload.metadata.source == scenario_generation.SCENARIO_SOURCE_LLM
    assert payload.metadata.model_name == "claude-opus-4.6"
    assert payload.metadata.model_version == "2024-11-15"
    assert payload.metadata.prompt_version == "v9"
    assert payload.metadata.rubric_version == "r9"
    assert payload.storyline_md.startswith("A custom storyline")
    assert payload.project_brief_md.startswith("# Project Brief")
    assert "target stack" not in payload.rubric_json["summary"].lower()
    assert "python" not in payload.rubric_json["summary"].lower()

    assert captured["agent_key"] == "prestart"
    assert captured["runtime_agent_key"] == "prestart"
    assert captured["policy_agent_key"] == "prestart"
    assert (
        'Company prompt overrides: {"tone": "pragmatic"}' in captured["run_context_md"]
    )
    assert (
        'Trial prompt overrides: {"scope": "end-to-end"}' in captured["run_context_md"]
    )
    assert (
        "Project brief guidance: blank-repo, from-scratch system design only."
        in captured["run_context_md"]
    )
    request = captured["request"]
    assert isinstance(request, ScenarioGenerationProviderRequest)
    assert request.model == "claude-opus-4.6"
    assert '"focus": "Emphasize production realism."' in request.user_prompt
    assert '"companyContext": {' in request.user_prompt
    assert '"domain": "payments"' in request.user_prompt
    assert '"productArea": "billing"' in request.user_prompt
    assert '"techStack"' not in request.user_prompt
    assert '"scenarioTemplate"' not in request.user_prompt
    assert '"preferredLanguageFramework": {' in request.user_prompt
    assert '"value": "TypeScript/Node"' in request.user_prompt
    assert '"binding": "context_only"' in request.user_prompt
    assert (
        "Preferred language/framework context (non-binding): TypeScript/Node"
        in captured["run_context_md"]
    )
    assert (
        "Treat any Talent Partner context as optional and non-binding."
        in captured["run_context_md"]
    )


def test_generate_scenario_payload_requires_snapshot() -> None:
    with pytest.raises(
        AIPolicySnapshotError, match="scenario_version_ai_policy_snapshot_missing"
    ):
        scenario_generation.generate_scenario_payload(
            role="Backend Engineer",
            tech_stack="Python",
            template_key="python-fastapi",
        )
