from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap


def _run_script(script: str) -> None:
    subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        check=True,
        cwd=pathlib.Path(__file__).resolve().parents[3],
    )


def test_openai_winoe_report_review_day_keeps_non_retryable_error_via_subprocess():
    _run_script(
        """
        import pathlib
        import sys

        sys.path.insert(0, str(pathlib.Path.cwd()))

        from app.ai.ai_provider_clients_service import AIProviderExecutionError
        from app.integrations.winoe_report_review import (
            WinoeReportDayReviewRequest,
            WinoeReportReviewProviderError,
        )
        from app.integrations.winoe_report_review import openai_provider_client as provider_module

        def _fake_openai_json_schema(**_kwargs):
            raise AIProviderExecutionError("openai_invalid_structured_output")

        provider_module.call_openai_json_schema = _fake_openai_json_schema
        provider_module.settings.OPENAI_API_KEY = "openai-test-key"
        provider_module.settings.ANTHROPIC_API_KEY = "anthropic-test-key"

        provider = provider_module.OpenAIWinoeReportReviewProvider()
        try:
            provider.review_day(
                request=WinoeReportDayReviewRequest(
                    system_prompt="system",
                    user_prompt="user",
                    model="gpt-5.4-mini",
                )
            )
        except WinoeReportReviewProviderError as exc:
            assert "openai_invalid_structured_output" in str(exc)
        else:
            raise AssertionError("expected WinoeReportReviewProviderError")
        """
    )


def test_openai_winoe_report_review_day_escalates_anthropic_model_after_invalid_output_via_subprocess():
    _run_script(
        """
        import pathlib
        import sys

        sys.path.insert(0, str(pathlib.Path.cwd()))

        from app.ai import DayReviewerOutput
        from app.ai.ai_provider_clients_service import AIProviderExecutionError
        from app.integrations.winoe_report_review import WinoeReportDayReviewRequest
        from app.integrations.winoe_report_review import openai_provider_client as provider_module

        calls = []

        def _reviewer_output():
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

        def _fake_openai_json_schema(**kwargs):
            calls.append(("openai", kwargs["model"]))
            raise AIProviderExecutionError("openai_request_failed:RateLimitError")

        def _fake_anthropic_json(**kwargs):
            calls.append(("anthropic", kwargs["model"]))
            if kwargs["model"] == "claude-haiku-4-5":
                raise AIProviderExecutionError("anthropic_invalid_json_output")
            return _reviewer_output()

        provider_module.call_openai_json_schema = _fake_openai_json_schema
        provider_module.call_anthropic_json = _fake_anthropic_json
        provider_module.settings.OPENAI_API_KEY = "openai-test-key"
        provider_module.settings.ANTHROPIC_API_KEY = "anthropic-test-key"
        provider_module.settings.WINOE_REPORT_ANTHROPIC_FALLBACK_DAY_MODEL = "claude-haiku-4-5"

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
            ("anthropic", "claude-sonnet-4-6"),
        ]
        """
    )
