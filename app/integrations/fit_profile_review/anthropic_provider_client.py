"""Anthropic-backed fit-profile review provider."""

from __future__ import annotations

from app.ai import AggregatedFitProfileOutput, DayReviewerOutput
from app.ai.ai_provider_clients_service import (
    AIProviderExecutionError,
    call_anthropic_json,
)
from app.config import settings
from app.integrations.fit_profile_review.base_client import (
    FitProfileAggregateRequest,
    FitProfileDayReviewRequest,
    FitProfileReviewProviderError,
)


class AnthropicFitProfileReviewProvider:
    """Run reviewer and aggregator calls via Anthropic JSON outputs."""

    def review_day(
        self,
        *,
        request: FitProfileDayReviewRequest,
    ) -> DayReviewerOutput:
        try:
            result = call_anthropic_json(
                api_key=settings.ANTHROPIC_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=DayReviewerOutput,
                timeout_seconds=max(
                    settings.FIT_PROFILE_DAY1_TIMEOUT_SECONDS,
                    settings.FIT_PROFILE_DAY23_TIMEOUT_SECONDS,
                    settings.FIT_PROFILE_DAY4_TIMEOUT_SECONDS,
                    settings.FIT_PROFILE_DAY5_TIMEOUT_SECONDS,
                ),
                max_retries=max(
                    settings.FIT_PROFILE_DAY1_MAX_RETRIES,
                    settings.FIT_PROFILE_DAY23_MAX_RETRIES,
                    settings.FIT_PROFILE_DAY4_MAX_RETRIES,
                    settings.FIT_PROFILE_DAY5_MAX_RETRIES,
                ),
            )
        except AIProviderExecutionError as exc:
            raise FitProfileReviewProviderError(str(exc)) from exc
        return result

    def aggregate_fit_profile(
        self,
        *,
        request: FitProfileAggregateRequest,
    ) -> AggregatedFitProfileOutput:
        try:
            result = call_anthropic_json(
                api_key=settings.ANTHROPIC_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=AggregatedFitProfileOutput,
                timeout_seconds=settings.FIT_PROFILE_AGGREGATOR_TIMEOUT_SECONDS,
                max_retries=settings.FIT_PROFILE_AGGREGATOR_MAX_RETRIES,
            )
        except AIProviderExecutionError as exc:
            raise FitProfileReviewProviderError(str(exc)) from exc
        return result


__all__ = ["AnthropicFitProfileReviewProvider"]
