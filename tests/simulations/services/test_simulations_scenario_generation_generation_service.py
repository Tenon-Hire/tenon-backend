from __future__ import annotations

import pytest

from app.simulations.services import scenario_generation


def test_deterministic_template_generation_is_stable_for_same_inputs() -> None:
    first = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python, FastAPI, PostgreSQL",
        template_key="python-fastapi",
    )
    second = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python, FastAPI, PostgreSQL",
        template_key="python-fastapi",
    )
    assert first == second
    assert len(first.task_prompts_json) == 5
    assert (
        first.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_choose_generation_source_prefers_fallback_without_llm_keys() -> None:
    source = scenario_generation.choose_generation_source(
        demo_mode_enabled=False,
        llm_available=False,
    )
    assert source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK


def test_choose_generation_source_prefers_fallback_in_demo_mode() -> None:
    source = scenario_generation.choose_generation_source(
        demo_mode_enabled=True,
        llm_available=True,
    )
    assert source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK


def test_generate_scenario_payload_uses_fallback_when_llm_credentials_missing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TENON_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TENON_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TENON_DEMO_MODE", raising=False)
    monkeypatch.delenv("TENON_SCENARIO_DEMO_MODE", raising=False)

    def _llm_should_not_run(*, role: str, tech_stack: str, template_key: str):
        raise AssertionError(
            "LLM generator should not execute when credentials are unavailable"
        )

    monkeypatch.setattr(scenario_generation, "_generate_with_llm", _llm_should_not_run)
    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
    )
    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_generate_scenario_payload_uses_fallback_in_demo_mode(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TENON_DEMO_MODE", "1")

    def _llm_should_not_run(*, role: str, tech_stack: str, template_key: str):
        raise AssertionError("LLM generator should not execute in demo mode")

    monkeypatch.setattr(scenario_generation, "_generate_with_llm", _llm_should_not_run)
    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
    )
    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_generate_scenario_payload_falls_back_when_llm_generation_errors(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("TENON_DEMO_MODE", raising=False)
    monkeypatch.delenv("TENON_SCENARIO_DEMO_MODE", raising=False)

    def _explode(*, role: str, tech_stack: str, template_key: str):
        raise RuntimeError("llm exploded")

    monkeypatch.setattr(scenario_generation, "_generate_with_llm", _explode)
    payload = scenario_generation.generate_scenario_payload(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="python-fastapi",
    )
    assert (
        payload.metadata.source == scenario_generation.SCENARIO_SOURCE_TEMPLATE_FALLBACK
    )


def test_template_display_name_falls_back_to_template_key_when_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(scenario_generation, "TEMPLATE_CATALOG", {})
    payload = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="missing-template",
    )
    assert "missing-template" in payload.storyline_md


def test_generate_with_llm_placeholder_raises() -> None:
    with pytest.raises(RuntimeError, match="llm_generation_not_implemented"):
        scenario_generation._generate_with_llm(
            role="Backend Engineer",
            tech_stack="Python",
            template_key="python-fastapi",
        )
