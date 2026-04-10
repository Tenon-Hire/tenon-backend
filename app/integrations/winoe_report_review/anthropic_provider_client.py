"""Anthropic-backed winoe-report review provider."""

from __future__ import annotations

from app.ai import AggregatedWinoeReportOutput, DayReviewerOutput
from app.ai.ai_provider_clients_service import (
    AIProviderExecutionError,
    call_anthropic_json,
)
from app.config import settings
from app.integrations.winoe_report_review.base_client import (
    WinoeReportAggregateRequest,
    WinoeReportDayReviewRequest,
    WinoeReportReviewProviderError,
)


class AnthropicWinoeReportReviewProvider:
    """Run reviewer and aggregator calls via Anthropic JSON outputs."""

    def review_day(
        self,
        *,
        request: WinoeReportDayReviewRequest,
    ) -> DayReviewerOutput:
        try:
            result = call_anthropic_json(
                api_key=settings.ANTHROPIC_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=DayReviewerOutput,
                timeout_seconds=max(
                    settings.WINOE_REPORT_DAY1_TIMEOUT_SECONDS,
                    settings.WINOE_REPORT_DAY23_TIMEOUT_SECONDS,
                    settings.WINOE_REPORT_DAY4_TIMEOUT_SECONDS,
                    settings.WINOE_REPORT_DAY5_TIMEOUT_SECONDS,
                ),
                max_retries=max(
                    settings.WINOE_REPORT_DAY1_MAX_RETRIES,
                    settings.WINOE_REPORT_DAY23_MAX_RETRIES,
                    settings.WINOE_REPORT_DAY4_MAX_RETRIES,
                    settings.WINOE_REPORT_DAY5_MAX_RETRIES,
                ),
            )
        except AIProviderExecutionError as exc:
            raise WinoeReportReviewProviderError(str(exc)) from exc
        return result

    def aggregate_winoe_report(
        self,
        *,
        request: WinoeReportAggregateRequest,
    ) -> AggregatedWinoeReportOutput:
        try:
            result = call_anthropic_json(
                api_key=settings.ANTHROPIC_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=AggregatedWinoeReportOutput,
                timeout_seconds=settings.WINOE_REPORT_AGGREGATOR_TIMEOUT_SECONDS,
                max_retries=settings.WINOE_REPORT_AGGREGATOR_MAX_RETRIES,
            )
        except AIProviderExecutionError as exc:
            raise WinoeReportReviewProviderError(str(exc)) from exc
        return result


__all__ = ["AnthropicWinoeReportReviewProvider"]
