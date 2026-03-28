"""Application module for perf middleware spans middleware workflows."""

from __future__ import annotations

import random

from .shared_perf_config import perf_span_sample_rate, perf_spans_enabled


def sample_perf_span() -> bool:
    """Execute sample perf span."""
    if not perf_spans_enabled():
        return False
    return random.random() <= perf_span_sample_rate()


def request_span_payload(
    *,
    request_id: str,
    method: str | None,
    path_template: str | None,
    status_code: int,
    duration_ms: float,
    response_bytes: int,
) -> dict[str, object]:
    """Execute request span payload."""
    return {
        "kind": "request",
        "requestId": request_id,
        "method": method,
        "route": path_template,
        "statusCode": status_code,
        "durationMs": round(duration_ms, 3),
        "responseBytes": int(response_bytes),
    }


def sql_span_payload(stats) -> dict[str, object]:
    """Execute sql span payload."""
    ranked = sorted(
        stats.sql_fingerprint_counts.items(),
        key=lambda item: stats.sql_fingerprint_time_ms.get(item[0], 0.0),
        reverse=True,
    )
    return {
        "kind": "sql",
        "count": int(stats.db_count),
        "totalMs": round(stats.db_time_ms, 3),
        "topFingerprints": [
            {
                "fingerprint": fingerprint,
                "count": int(count),
                "timeMs": round(stats.sql_fingerprint_time_ms.get(fingerprint, 0.0), 3),
            }
            for fingerprint, count in ranked[:5]
        ],
    }


def external_span_payload(stats) -> dict[str, object]:
    """Execute external span payload."""
    details = []
    total_calls = 0
    total_wait = 0.0
    for provider in sorted(stats.external_call_counts):
        calls = int(stats.external_call_counts.get(provider, 0))
        wait_ms = float(stats.external_wait_ms.get(provider, 0.0))
        total_calls += calls
        total_wait += wait_ms
        details.append(
            {"provider": provider, "calls": calls, "waitMs": round(wait_ms, 3)}
        )
    return {
        "kind": "external",
        "totalCalls": total_calls,
        "totalWaitMs": round(total_wait, 3),
        "providers": details,
    }
