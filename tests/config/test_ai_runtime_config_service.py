from __future__ import annotations

from app.ai import (
    resolve_scenario_generation_config,
    resolve_transcription_config,
    resolve_winoe_report_aggregator_config,
    resolve_winoe_report_code_implementation_config,
    resolve_winoe_report_day1_config,
    resolve_winoe_report_day4_config,
    resolve_winoe_report_day5_config,
)


def test_resolve_winoe_report_day1_config_defaults_to_claude_opus_4_7():
    config = resolve_winoe_report_day1_config()

    assert config.provider == "anthropic"
    assert config.model == "claude-opus-4-7"


def test_resolve_active_ai_runtime_mappings_stay_aligned():
    assert resolve_scenario_generation_config().provider == "anthropic"
    assert resolve_scenario_generation_config().model == "claude-opus-4-7"

    assert resolve_winoe_report_code_implementation_config().provider == "openai"
    assert resolve_winoe_report_code_implementation_config().model == "gpt-5.2-codex"

    assert resolve_winoe_report_day4_config().provider == "anthropic"
    assert resolve_winoe_report_day4_config().model == "claude-sonnet-4-6"

    assert resolve_winoe_report_day5_config().provider == "anthropic"
    assert resolve_winoe_report_day5_config().model == "claude-sonnet-4-6"

    assert resolve_winoe_report_aggregator_config().provider == "openai"
    assert resolve_winoe_report_aggregator_config().model == "gpt-5.2"

    assert resolve_transcription_config().provider == "openai"
    assert resolve_transcription_config().model == "gpt-4o-transcribe"
