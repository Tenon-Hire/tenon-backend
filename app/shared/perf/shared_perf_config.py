"""Application module for perf config workflows."""

from app.config import settings


def perf_logging_enabled() -> bool:
    """Return True when request perf instrumentation is enabled."""
    return bool(
        getattr(settings, "DEBUG_PERF", False)
        or getattr(settings, "PERF_SPANS_ENABLED", False)
    )


def perf_spans_enabled() -> bool:
    """Execute perf spans enabled."""
    return bool(getattr(settings, "PERF_SPANS_ENABLED", False))


def perf_sql_fingerprints_enabled() -> bool:
    """Execute perf sql fingerprints enabled."""
    return bool(getattr(settings, "PERF_SQL_FINGERPRINTS_ENABLED", False))


def perf_span_sample_rate() -> float:
    """Execute perf span sample rate."""
    rate = getattr(settings, "PERF_SPAN_SAMPLE_RATE", 1.0)
    try:
        value = float(rate)
    except (TypeError, ValueError):
        return 1.0
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


__all__ = [
    "perf_logging_enabled",
    "perf_spans_enabled",
    "perf_sql_fingerprints_enabled",
    "perf_span_sample_rate",
    "settings",
]
