"""Application module for perf context utils workflows."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field


@dataclass
class PerfStats:
    """Lightweight per-request DB stats."""

    db_count: int = 0
    db_time_ms: float = 0.0
    sql_fingerprint_counts: dict[str, int] = field(default_factory=dict)
    sql_fingerprint_time_ms: dict[str, float] = field(default_factory=dict)
    external_call_counts: dict[str, int] = field(default_factory=dict)
    external_wait_ms: dict[str, float] = field(default_factory=dict)

    def record_sql(self, fingerprint: str, elapsed_ms: float) -> None:
        """Record sql."""
        normalized = (fingerprint or "").strip()
        if not normalized:
            return
        self.sql_fingerprint_counts[normalized] = (
            self.sql_fingerprint_counts.get(normalized, 0) + 1
        )
        self.sql_fingerprint_time_ms[normalized] = self.sql_fingerprint_time_ms.get(
            normalized, 0.0
        ) + float(elapsed_ms)

    def record_external_wait(self, provider: str, elapsed_ms: float) -> None:
        """Record external wait."""
        normalized_provider = (provider or "").strip().lower() or "unknown"
        self.external_call_counts[normalized_provider] = (
            self.external_call_counts.get(normalized_provider, 0) + 1
        )
        self.external_wait_ms[normalized_provider] = self.external_wait_ms.get(
            normalized_provider, 0.0
        ) + float(elapsed_ms)


def start_request_stats(perf_ctx: ContextVar) -> Token:
    """Initialize per-request stats in the provided ContextVar."""
    return perf_ctx.set(PerfStats())


def get_request_stats(perf_ctx: ContextVar) -> PerfStats:
    """Fetch current per-request stats (returns an empty instance by default)."""
    stats = perf_ctx.get()
    if stats is None:
        return PerfStats()
    return stats


def clear_request_stats(perf_ctx: ContextVar, token: Token) -> None:
    """Clear request stats ContextVar, ignoring reset errors."""
    try:
        perf_ctx.reset(token)
    except Exception:
        perf_ctx.set(None)


__all__ = [
    "PerfStats",
    "start_request_stats",
    "get_request_stats",
    "clear_request_stats",
]
