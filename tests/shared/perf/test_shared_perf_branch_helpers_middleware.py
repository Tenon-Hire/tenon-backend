from __future__ import annotations

import random
from types import SimpleNamespace

import pytest

from app.shared.perf import shared_perf_config as perf_config
from app.shared.perf import shared_perf_context_utils as perf_context
from app.shared.perf import shared_perf_middleware_spans_middleware as perf_spans
from app.shared.perf import shared_perf_sqlalchemy_hooks_utils as perf_sql


@pytest.mark.parametrize(
    ("configured_rate", "expected"),
    [
        ("not-a-number", 1.0),
        (-1.0, 0.0),
        (2.5, 1.0),
        (0.25, 0.25),
    ],
)
def test_perf_span_sample_rate_clamps_and_defaults(
    monkeypatch, configured_rate, expected: float
):
    monkeypatch.setattr(perf_config.settings, "PERF_SPAN_SAMPLE_RATE", configured_rate)
    assert perf_config.perf_span_sample_rate() == expected


def test_sample_perf_span_honors_feature_flag_and_sample_rate(monkeypatch):
    monkeypatch.setattr(perf_spans, "perf_spans_enabled", lambda: False)
    assert perf_spans.sample_perf_span() is False

    monkeypatch.setattr(perf_spans, "perf_spans_enabled", lambda: True)
    monkeypatch.setattr(perf_spans, "perf_span_sample_rate", lambda: 0.5)
    monkeypatch.setattr(random, "random", lambda: 0.6)
    assert perf_spans.sample_perf_span() is False

    monkeypatch.setattr(random, "random", lambda: 0.4)
    assert perf_spans.sample_perf_span() is True


def test_span_payload_helpers_cover_sorting_and_aggregation():
    stats = perf_context.PerfStats()
    stats.db_count = 7
    stats.db_time_ms = 12.34567
    stats.sql_fingerprint_counts = {"fast": 8, "slow": 2, "medium": 4}
    stats.sql_fingerprint_time_ms = {"fast": 2.0, "slow": 10.0, "medium": 5.0}
    stats.external_call_counts = {"zeta": 1, "alpha": 3}
    stats.external_wait_ms = {"zeta": 1.2, "alpha": 4.8}

    request_payload = perf_spans.request_span_payload(
        request_id="req-1",
        method="GET",
        path_template="/api/example",
        status_code=200,
        duration_ms=10.5555,
        response_bytes=123.4,
    )
    sql_payload = perf_spans.sql_span_payload(stats)
    external_payload = perf_spans.external_span_payload(stats)

    assert request_payload["durationMs"] == 10.556
    assert request_payload["responseBytes"] == 123
    assert sql_payload["count"] == 7
    assert sql_payload["totalMs"] == 12.346
    assert [item["fingerprint"] for item in sql_payload["topFingerprints"]] == [
        "slow",
        "medium",
        "fast",
    ]
    assert external_payload["totalCalls"] == 4
    assert external_payload["totalWaitMs"] == 6.0
    assert [item["provider"] for item in external_payload["providers"]] == [
        "alpha",
        "zeta",
    ]


def test_perf_context_record_and_clear_edge_paths():
    stats = perf_context.PerfStats()
    stats.record_sql("   ", 1.0)
    assert stats.sql_fingerprint_counts == {}
    assert stats.sql_fingerprint_time_ms == {}

    stats.record_sql(" SELECT 1 ", 2.5)
    assert stats.sql_fingerprint_counts["SELECT 1"] == 1
    assert stats.sql_fingerprint_time_ms["SELECT 1"] == 2.5

    stats.record_external_wait(" OpenAI ", 3.0)
    assert stats.external_call_counts["openai"] == 1
    assert stats.external_wait_ms["openai"] == 3.0

    class _BrokenContextVar:
        def __init__(self):
            self.value = "unchanged"

        def reset(self, _token):
            raise RuntimeError("boom")

        def set(self, value):
            self.value = value

    broken_context = _BrokenContextVar()
    perf_context.clear_request_stats(broken_context, SimpleNamespace())
    assert broken_context.value is None


def test_sql_normalization_edge_branches():
    assert perf_sql.normalize_sql_statement(None) == ""

    normalized = perf_sql.normalize_sql_statement(
        "SELECT  *   FROM events WHERE id IN (?, :name, :other) "
        "AND signature=0xABCDEF AND note='hello world'"
    )
    assert "(?)" in normalized
    assert "0xabcdef" not in normalized
    assert "hello world" not in normalized
    assert "  " not in normalized

    oversized = "x" * 700
    assert len(perf_sql.normalize_sql_statement(oversized)) == 512


def test_sqlalchemy_hooks_record_fingerprint_when_enabled(monkeypatch):
    class _EventImpl:
        def __init__(self) -> None:
            self.handlers = {}

        def listens_for(self, _target, name):
            def _decorator(fn):
                self.handlers[name] = fn
                return fn

            return _decorator

    class _Stats:
        def __init__(self) -> None:
            self.db_count = 0
            self.db_time_ms = 0.0
            self.recorded: tuple[str, float] | None = None

        def record_sql(self, fingerprint: str, elapsed_ms: float) -> None:
            self.recorded = (fingerprint, elapsed_ms)

    counter = iter([100.0, 100.25])
    monkeypatch.setattr(perf_sql.time, "perf_counter", lambda: next(counter))

    event_impl = _EventImpl()
    stats = _Stats()
    perf_sql.register_listeners(
        SimpleNamespace(sync_engine=object()),
        event_impl=event_impl,
        perf_ctx=SimpleNamespace(get=lambda: stats),
        perf_module=SimpleNamespace(
            perf_logging_enabled=lambda: True,
            perf_sql_fingerprints_enabled=lambda: True,
        ),
    )

    context = SimpleNamespace()
    event_impl.handlers["before_cursor_execute"](
        None,
        None,
        "SELECT 42",
        None,
        context,
        None,
    )
    event_impl.handlers["after_cursor_execute"](None, None, None, None, context, None)

    assert stats.db_count == 1
    assert stats.db_time_ms == pytest.approx(250.0)
    assert stats.recorded is not None
    assert stats.recorded[0] == "select ?"
    assert stats.recorded[1] == pytest.approx(250.0)
