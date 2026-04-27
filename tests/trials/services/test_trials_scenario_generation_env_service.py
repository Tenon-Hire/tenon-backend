from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.trials.services import (
    trials_services_trials_scenario_generation_env_service as scenario_env_service,
)


def test_is_demo_mode_enabled_delegates_to_runtime_mode(monkeypatch):
    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="demo", provider="openai"),
    )

    assert scenario_env_service.is_demo_mode_enabled() is True


def test_is_demo_mode_enabled_honors_settings_override(monkeypatch):
    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="openai"),
    )
    monkeypatch.setattr(scenario_env_service.settings, "DEMO_MODE", True)

    assert scenario_env_service.is_demo_mode_enabled() is True


def test_is_demo_mode_enabled_honors_demo_env_key(monkeypatch):
    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="openai"),
    )
    monkeypatch.setenv("WINOE_DEMO_MODE", "1")

    assert scenario_env_service.is_demo_mode_enabled() is True


def test_llm_credentials_available_covers_provider_branches(monkeypatch):
    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="openai"),
    )
    monkeypatch.setattr(scenario_env_service.settings, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(
        scenario_env_service.settings, "ANTHROPIC_API_KEY", "anthropic-key"
    )

    assert scenario_env_service.llm_credentials_available() is True

    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="anthropic"),
    )
    assert scenario_env_service.llm_credentials_available() is True

    monkeypatch.setattr(
        scenario_env_service,
        "resolve_scenario_generation_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="other"),
    )
    assert scenario_env_service.llm_credentials_available() is False


def test_choose_generation_source_handles_demo_and_errors():
    assert (
        scenario_env_service.choose_generation_source(demo_mode_enabled=True)
        == scenario_env_service.SCENARIO_SOURCE_DETERMINISTIC_FALLBACK
    )
    assert (
        scenario_env_service.choose_generation_source(
            demo_mode_enabled=False, llm_available=True
        )
        == scenario_env_service.SCENARIO_SOURCE_LLM
    )
    with pytest.raises(RuntimeError, match="scenario_generation_provider_unavailable"):
        scenario_env_service.choose_generation_source(
            demo_mode_enabled=False, llm_available=False
        )


def test_choose_generation_source_defaults_to_llm_when_available(monkeypatch):
    monkeypatch.setattr(scenario_env_service, "is_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(scenario_env_service, "llm_credentials_available", lambda: True)
    assert (
        scenario_env_service.choose_generation_source()
        == scenario_env_service.SCENARIO_SOURCE_LLM
    )
