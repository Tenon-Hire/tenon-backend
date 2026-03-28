"""Application module for simulations services simulations scenario generation env service workflows."""

from __future__ import annotations

import os

from app.simulations.services.simulations_services_simulations_scenario_generation_constants import (
    ANTHROPIC_API_ENV_KEYS,
    DEMO_MODE_ENV_KEYS,
    OPENAI_API_ENV_KEYS,
    SCENARIO_SOURCE_LLM,
    SCENARIO_SOURCE_TEMPLATE_FALLBACK,
)


def _truthy_env(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _has_any_env(keys: tuple[str, ...]) -> bool:
    return any((os.getenv(key) or "").strip() for key in keys)


def is_demo_mode_enabled() -> bool:
    """Return whether demo mode enabled."""
    return any(_truthy_env(os.getenv(key)) for key in DEMO_MODE_ENV_KEYS)


def llm_credentials_available() -> bool:
    """Execute llm credentials available."""
    return _has_any_env(OPENAI_API_ENV_KEYS + ANTHROPIC_API_ENV_KEYS)


def choose_generation_source(
    *,
    demo_mode_enabled: bool | None = None,
    llm_available: bool | None = None,
) -> str:
    """Choose generation source."""
    if demo_mode_enabled is None:
        demo_mode_enabled = is_demo_mode_enabled()
    if demo_mode_enabled:
        return SCENARIO_SOURCE_TEMPLATE_FALLBACK
    if llm_available is None:
        llm_available = llm_credentials_available()
    if not llm_available:
        return SCENARIO_SOURCE_TEMPLATE_FALLBACK
    return SCENARIO_SOURCE_LLM


__all__ = [
    "choose_generation_source",
    "is_demo_mode_enabled",
    "llm_credentials_available",
]
