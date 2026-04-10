"""Winoe Report review provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.integrations.winoe_report_review.anthropic_provider_client import (
    AnthropicWinoeReportReviewProvider,
)
from app.integrations.winoe_report_review.base_client import WinoeReportReviewProvider
from app.integrations.winoe_report_review.openai_provider_client import (
    OpenAIWinoeReportReviewProvider,
)


@lru_cache(maxsize=4)
def get_winoe_report_review_provider(provider: str) -> WinoeReportReviewProvider:
    """Return the configured winoe-report review provider."""
    normalized = (provider or "").strip().lower()
    if normalized == "anthropic":
        return AnthropicWinoeReportReviewProvider()
    if normalized == "openai":
        return OpenAIWinoeReportReviewProvider()
    raise ValueError(f"Unsupported winoe report provider: {provider}")


__all__ = ["get_winoe_report_review_provider"]
