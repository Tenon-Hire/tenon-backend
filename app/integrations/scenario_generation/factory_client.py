"""Scenario-generation provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.ai import resolve_scenario_generation_config
from app.integrations.scenario_generation.anthropic_provider_client import (
    AnthropicScenarioGenerationProvider,
)
from app.integrations.scenario_generation.base_client import (
    ScenarioGenerationProvider,
)
from app.integrations.scenario_generation.openai_provider_client import (
    OpenAIScenarioGenerationProvider,
)


@lru_cache(maxsize=4)
def get_scenario_generation_provider(
    provider: str | None = None,
) -> ScenarioGenerationProvider:
    """Return the configured scenario-generation provider."""
    normalized = (
        (provider or "").strip().lower()
        or resolve_scenario_generation_config().provider
    )
    if normalized == "anthropic":
        return AnthropicScenarioGenerationProvider()
    if normalized == "openai":
        return OpenAIScenarioGenerationProvider()
    raise ValueError(f"Unsupported scenario generation provider: {provider}")


__all__ = ["get_scenario_generation_provider"]
