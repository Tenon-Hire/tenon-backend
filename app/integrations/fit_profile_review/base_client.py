"""Fit-profile review provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ai import AggregatedFitProfileOutput, DayReviewerOutput


class FitProfileReviewProviderError(RuntimeError):
    """Raised when fit-profile review provider execution fails."""


@dataclass(frozen=True, slots=True)
class FitProfileDayReviewRequest:
    """Structured request for a single reviewer agent."""

    system_prompt: str
    user_prompt: str
    model: str


@dataclass(frozen=True, slots=True)
class FitProfileAggregateRequest:
    """Structured request for the fit-profile aggregator."""

    system_prompt: str
    user_prompt: str
    model: str


class FitProfileReviewProvider(Protocol):
    """Provider contract for fit-profile review workloads."""

    def review_day(
        self,
        *,
        request: FitProfileDayReviewRequest,
    ) -> DayReviewerOutput:
        """Review one day artifact."""
        ...

    def aggregate_fit_profile(
        self,
        *,
        request: FitProfileAggregateRequest,
    ) -> AggregatedFitProfileOutput:
        """Aggregate reviewer outputs into one fit profile."""
        ...


__all__ = [
    "FitProfileAggregateRequest",
    "FitProfileDayReviewRequest",
    "FitProfileReviewProvider",
    "FitProfileReviewProviderError",
]
