"""Application module for simulations services simulations scenario generation env service workflows."""

from __future__ import annotations

from app.ai import (
    allow_demo_or_test_mode,
    resolve_scenario_generation_config,
)
from app.ai.ai_provider_clients_service import api_key_configured
from app.config import settings
from app.simulations.services.simulations_services_simulations_scenario_generation_constants import (
    SCENARIO_SOURCE_LLM,
    SCENARIO_SOURCE_TEMPLATE_FALLBACK,
)


def is_demo_mode_enabled() -> bool:
    """Return whether demo mode enabled."""
    return allow_demo_or_test_mode(resolve_scenario_generation_config().runtime_mode)


def llm_credentials_available() -> bool:
    """Execute llm credentials available."""
    provider = resolve_scenario_generation_config().provider
    if provider == "anthropic":
        return api_key_configured(settings.ANTHROPIC_API_KEY)
    if provider == "openai":
        return api_key_configured(settings.OPENAI_API_KEY)
    return False


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
        raise RuntimeError("scenario_generation_provider_unavailable")
    return SCENARIO_SOURCE_LLM


__all__ = [
    "choose_generation_source",
    "is_demo_mode_enabled",
    "llm_credentials_available",
]
