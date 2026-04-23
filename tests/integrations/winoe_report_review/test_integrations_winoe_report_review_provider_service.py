from __future__ import annotations

import pytest

from app.ai import AggregatedWinoeReportOutput, DayReviewerOutput
from app.ai.ai_provider_clients_service import AIProviderExecutionError
from app.integrations.winoe_report_review import (
    WinoeReportAggregateRequest,
    WinoeReportDayReviewRequest,
    WinoeReportReviewProviderError,
)
from app.integrations.winoe_report_review import (
    openai_provider_client as provider_module,
)


def _reviewer_output() -> DayReviewerOutput:
    return DayReviewerOutput.model_validate(
        {
            "dayIndex": 2,
            "score": 0.78,
            "summary": "The candidate completed the implementation with clear checkpoints.",
            "rubricBreakdown": {"execution": 0.8, "communication": 0.76},
            "evidence": [
                {
                    "kind": "submission",
                    "ref": "submission://day2",
                    "quote": "Implemented the retry path and documented the tradeoff.",
                    "dayIndex": 2,
                }
            ],
            "strengths": ["Delivered the core fix."],
            "risks": ["Could tighten test coverage."],
        }
    )


def _aggregated_output(*, reason: str | None = None) -> AggregatedWinoeReportOutput:
    return AggregatedWinoeReportOutput.model_validate(
        {
            "overallWinoeScore": 0.82,
            "recommendation": "positive_signal",
            "confidence": 0.74,
            "dayScores": [
                {
                    "dayIndex": 2,
                    "status": "scored",
                    "score": 0.82,
                    "rubricBreakdown": {"execution": 0.84},
                    "evidence": [
                        {
                            "kind": "submission",
                            "ref": "submission://day2",
                            "quote": "The candidate closed the blocking issue.",
                            "dayIndex": 2,
                        }
                    ],
                    "reason": reason,
                }
            ],
            "strengths": ["Strong execution under constraints."],
            "risks": ["Limited time for polish."],
            "calibrationText": "The evidence supports a positive signal.",
        }
    )


@pytest.mark.asyncio
async def test_openai_winoe_report_review_day_falls_back_to_anthropic_on_retryable_error(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_openai_json_schema(**kwargs):
        calls.append(("openai", kwargs["model"]))
        raise AIProviderExecutionError("openai_request_failed:RateLimitError")

    def _fake_anthropic_json(**kwargs):
        calls.append(("anthropic", kwargs["model"]))
        return _reviewer_output()

    monkeypatch.setattr(
        provider_module, "call_openai_json_schema", _fake_openai_json_schema
    )
    monkeypatch.setattr(provider_module, "call_anthropic_json", _fake_anthropic_json)
    monkeypatch.setattr(provider_module.settings, "OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr(
        provider_module.settings, "ANTHROPIC_API_KEY", "anthropic-test-key"
    )
    monkeypatch.setattr(
        provider_module.settings,
        "WINOE_REPORT_ANTHROPIC_FALLBACK_DAY_MODEL",
        "claude-haiku-4-5",
    )

    provider = provider_module.OpenAIWinoeReportReviewProvider()
    result = provider.review_day(
        request=WinoeReportDayReviewRequest(
            system_prompt="system",
            user_prompt="user",
            model="gpt-5.4-mini",
        )
    )

    assert result.dayIndex == 2
    assert calls == [
        ("openai", "gpt-5.4-mini"),
        ("anthropic", "claude-haiku-4-5"),
    ]


@pytest.mark.asyncio
async def test_openai_winoe_report_aggregate_falls_back_to_anthropic_on_retryable_error(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_openai_json_schema(**kwargs):
        calls.append(("openai", kwargs["model"]))
        raise AIProviderExecutionError("openai_request_failed:RateLimitError")

    def _fake_anthropic_json(**kwargs):
        calls.append(("anthropic", kwargs["model"]))
        return _aggregated_output()

    monkeypatch.setattr(
        provider_module, "call_openai_json_schema", _fake_openai_json_schema
    )
    monkeypatch.setattr(provider_module, "call_anthropic_json", _fake_anthropic_json)
    monkeypatch.setattr(provider_module.settings, "OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr(
        provider_module.settings, "ANTHROPIC_API_KEY", "anthropic-test-key"
    )
    monkeypatch.setattr(
        provider_module.settings,
        "WINOE_REPORT_ANTHROPIC_FALLBACK_AGGREGATOR_MODEL",
        "claude-sonnet-4-6",
    )

    provider = provider_module.OpenAIWinoeReportReviewProvider()
    result = provider.aggregate_winoe_report(
        request=WinoeReportAggregateRequest(
            system_prompt="system",
            user_prompt="user",
            model="gpt-5.2",
        )
    )

    assert result.recommendation == "positive_signal"
    assert calls == [
        ("openai", "gpt-5.2"),
        ("anthropic", "claude-sonnet-4-6"),
    ]


@pytest.mark.asyncio
async def test_openai_winoe_report_aggregate_accepts_long_anthropic_day_reason(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []
    long_reason = (
        "This rationale remains within the product contract but exceeds the earlier provider cap. "
        * 12
    )

    def _fake_openai_json_schema(**kwargs):
        calls.append(("openai", kwargs["model"]))
        raise AIProviderExecutionError("openai_request_failed:RateLimitError")

    def _fake_anthropic_json(**kwargs):
        calls.append(("anthropic", kwargs["model"]))
        return _aggregated_output(reason=long_reason)

    monkeypatch.setattr(
        provider_module, "call_openai_json_schema", _fake_openai_json_schema
    )
    monkeypatch.setattr(provider_module, "call_anthropic_json", _fake_anthropic_json)
    monkeypatch.setattr(provider_module.settings, "OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr(
        provider_module.settings, "ANTHROPIC_API_KEY", "anthropic-test-key"
    )
    monkeypatch.setattr(
        provider_module.settings,
        "WINOE_REPORT_ANTHROPIC_FALLBACK_AGGREGATOR_MODEL",
        "claude-sonnet-4-6",
    )

    provider = provider_module.OpenAIWinoeReportReviewProvider()
    result = provider.aggregate_winoe_report(
        request=WinoeReportAggregateRequest(
            system_prompt="system",
            user_prompt="user",
            model="gpt-5.2",
        )
    )

    assert result.dayScores[0].reason == long_reason
    assert calls == [
        ("openai", "gpt-5.2"),
        ("anthropic", "claude-sonnet-4-6"),
    ]
