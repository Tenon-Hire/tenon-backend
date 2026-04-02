"""Codespace-specializer provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.ai import resolve_codespace_specializer_config
from app.integrations.codespace_specializer.anthropic_provider_client import (
    AnthropicCodespaceSpecializerProvider,
)
from app.integrations.codespace_specializer.base_client import (
    CodespaceSpecializerProvider,
)
from app.integrations.codespace_specializer.openai_provider_client import (
    OpenAICodespaceSpecializerProvider,
)


@lru_cache(maxsize=4)
def get_codespace_specializer_provider(
    provider: str | None = None,
) -> CodespaceSpecializerProvider:
    """Return the configured codespace-specializer provider."""
    normalized = (
        (provider or "").strip().lower()
        or resolve_codespace_specializer_config().provider
    )
    if normalized == "openai":
        return OpenAICodespaceSpecializerProvider()
    if normalized == "anthropic":
        return AnthropicCodespaceSpecializerProvider()
    raise ValueError(f"Unsupported codespace specializer provider: {provider}")


__all__ = ["get_codespace_specializer_provider"]
