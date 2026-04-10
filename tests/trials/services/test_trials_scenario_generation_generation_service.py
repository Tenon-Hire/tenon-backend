from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import AIPolicySnapshotError, build_ai_policy_snapshot
from app.integrations.scenario_generation.base_client import (
    ScenarioGenerationProviderError,
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
        tech_stack: str,
        template_key: str,
        scenario_template=None,
        focus=None,
        company_context=None,
        company_prompt_overrides_json=None,
        trial_prompt_overrides_json=None,
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


def test_generate_scenario_payload_degrades_to_fallback_on_retryable_provider_error(
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

    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
        ai_policy_snapshot_json=_snapshot(),
    )

    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
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


def test_template_display_name_falls_back_to_template_key_when_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(scenario_generation, "TEMPLATE_CATALOG", {})
    payload = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="missing-template",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert "missing-template" in payload.storyline_md


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

    assert "demo presentation" in day4["description"].lower()
    assert "reflection essay" in day5["description"].lower()
    assert "demo presentation" in payload.rubric_json["summary"].lower()
    assert any(
        dimension["name"] == "Communication and presentation"
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
            tech_stack="Python",
            template_key="python-fastapi",
            ai_policy_snapshot_json=_snapshot(),
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
