"""Fit-profile review provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.integrations.fit_profile_review.anthropic_provider_client import (
    AnthropicFitProfileReviewProvider,
)
from app.integrations.fit_profile_review.base_client import FitProfileReviewProvider
from app.integrations.fit_profile_review.openai_provider_client import (
    OpenAIFitProfileReviewProvider,
)


@lru_cache(maxsize=4)
def get_fit_profile_review_provider(provider: str) -> FitProfileReviewProvider:
    """Return the configured fit-profile review provider."""
    normalized = (provider or "").strip().lower()
    if normalized == "anthropic":
        return AnthropicFitProfileReviewProvider()
    if normalized == "openai":
        return OpenAIFitProfileReviewProvider()
    raise ValueError(f"Unsupported fit profile provider: {provider}")


__all__ = ["get_fit_profile_review_provider"]
