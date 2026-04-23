"""Feature-level AI runtime configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

AI_RUNTIME_MODE_REAL = "real"
AI_RUNTIME_MODE_DEMO = "demo"
AI_RUNTIME_MODE_TEST = "test"
_ALLOWED_RUNTIME_MODES = {
    AI_RUNTIME_MODE_REAL,
    AI_RUNTIME_MODE_DEMO,
    AI_RUNTIME_MODE_TEST,
}


@dataclass(frozen=True, slots=True)
class AIFeatureConfig:
    """Resolved AI runtime configuration for one feature."""

    runtime_mode: str
    provider: str
    model: str
    timeout_seconds: int
    max_retries: int


def _normalize_runtime_mode(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _ALLOWED_RUNTIME_MODES:
        return normalized
    if str(settings.ENV or "").strip().lower() == "test":
        return AI_RUNTIME_MODE_TEST
    return AI_RUNTIME_MODE_REAL


def resolve_runtime_mode(feature_mode: str | None = None) -> str:
    """Resolve feature runtime mode with global fallback."""
    feature_resolved = _normalize_runtime_mode(feature_mode)
    if feature_resolved != AI_RUNTIME_MODE_REAL or feature_mode:
        return feature_resolved
    return _normalize_runtime_mode(getattr(settings, "AI_RUNTIME_MODE", None))


def allow_demo_or_test_mode(runtime_mode: str) -> bool:
    """Return whether deterministic or fake providers are allowed."""
    return runtime_mode in {AI_RUNTIME_MODE_DEMO, AI_RUNTIME_MODE_TEST}


def require_real_mode(runtime_mode: str) -> bool:
    """Return whether the feature must fail closed on provider errors."""
    return runtime_mode == AI_RUNTIME_MODE_REAL


def _build_feature_config(
    *,
    runtime_mode: str | None,
    provider: str,
    model: str,
    timeout_seconds: int,
    max_retries: int,
) -> AIFeatureConfig:
    return AIFeatureConfig(
        runtime_mode=resolve_runtime_mode(runtime_mode),
        provider=(provider or "").strip().lower(),
        model=(model or "").strip(),
        timeout_seconds=max(1, int(timeout_seconds)),
        max_retries=max(0, int(max_retries)),
    )


def resolve_scenario_generation_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "SCENARIO_GENERATION_RUNTIME_MODE", None),
        provider=settings.SCENARIO_GENERATION_PROVIDER,
        model=settings.SCENARIO_GENERATION_MODEL,
        timeout_seconds=settings.SCENARIO_GENERATION_TIMEOUT_SECONDS,
        max_retries=settings.SCENARIO_GENERATION_MAX_RETRIES,
    )


def resolve_codespace_specializer_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "CODESPACE_SPECIALIZER_RUNTIME_MODE", None),
        provider=settings.CODESPACE_SPECIALIZER_PROVIDER,
        model=settings.CODESPACE_SPECIALIZER_MODEL,
        timeout_seconds=settings.CODESPACE_SPECIALIZER_TIMEOUT_SECONDS,
        max_retries=settings.CODESPACE_SPECIALIZER_MAX_RETRIES,
    )


def resolve_winoe_report_day1_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "WINOE_REPORT_DAY1_RUNTIME_MODE", None),
        provider=settings.WINOE_REPORT_DAY1_PROVIDER,
        model=settings.WINOE_REPORT_DAY1_MODEL,
        timeout_seconds=settings.WINOE_REPORT_DAY1_TIMEOUT_SECONDS,
        max_retries=settings.WINOE_REPORT_DAY1_MAX_RETRIES,
    )


def resolve_winoe_report_code_implementation_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "WINOE_REPORT_DAY23_RUNTIME_MODE", None),
        provider=settings.WINOE_REPORT_DAY23_PROVIDER,
        model=settings.WINOE_REPORT_DAY23_MODEL,
        timeout_seconds=settings.WINOE_REPORT_DAY23_TIMEOUT_SECONDS,
        max_retries=settings.WINOE_REPORT_DAY23_MAX_RETRIES,
    )


def resolve_winoe_report_day23_config() -> AIFeatureConfig:
    return resolve_winoe_report_code_implementation_config()


def resolve_winoe_report_day4_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "WINOE_REPORT_DAY4_RUNTIME_MODE", None),
        provider=settings.WINOE_REPORT_DAY4_PROVIDER,
        model=settings.WINOE_REPORT_DAY4_MODEL,
        timeout_seconds=settings.WINOE_REPORT_DAY4_TIMEOUT_SECONDS,
        max_retries=settings.WINOE_REPORT_DAY4_MAX_RETRIES,
    )


def resolve_winoe_report_day5_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "WINOE_REPORT_DAY5_RUNTIME_MODE", None),
        provider=settings.WINOE_REPORT_DAY5_PROVIDER,
        model=settings.WINOE_REPORT_DAY5_MODEL,
        timeout_seconds=settings.WINOE_REPORT_DAY5_TIMEOUT_SECONDS,
        max_retries=settings.WINOE_REPORT_DAY5_MAX_RETRIES,
    )


def resolve_winoe_report_aggregator_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "WINOE_REPORT_AGGREGATOR_RUNTIME_MODE", None),
        provider=settings.WINOE_REPORT_AGGREGATOR_PROVIDER,
        model=settings.WINOE_REPORT_AGGREGATOR_MODEL,
        timeout_seconds=settings.WINOE_REPORT_AGGREGATOR_TIMEOUT_SECONDS,
        max_retries=settings.WINOE_REPORT_AGGREGATOR_MAX_RETRIES,
    )


def resolve_transcription_config() -> AIFeatureConfig:
    return _build_feature_config(
        runtime_mode=getattr(settings, "TRANSCRIPTION_RUNTIME_MODE", None),
        provider=settings.TRANSCRIPTION_PROVIDER,
        model=settings.TRANSCRIPTION_MODEL,
        timeout_seconds=settings.TRANSCRIPTION_TIMEOUT_SECONDS,
        max_retries=settings.TRANSCRIPTION_MAX_RETRIES,
    )


__all__ = [
    "AIFeatureConfig",
    "AI_RUNTIME_MODE_DEMO",
    "AI_RUNTIME_MODE_REAL",
    "AI_RUNTIME_MODE_TEST",
    "allow_demo_or_test_mode",
    "require_real_mode",
    "resolve_codespace_specializer_config",
    "resolve_winoe_report_aggregator_config",
    "resolve_winoe_report_day1_config",
    "resolve_winoe_report_code_implementation_config",
    "resolve_winoe_report_day23_config",
    "resolve_winoe_report_day4_config",
    "resolve_winoe_report_day5_config",
    "resolve_runtime_mode",
    "resolve_scenario_generation_config",
    "resolve_transcription_config",
]
