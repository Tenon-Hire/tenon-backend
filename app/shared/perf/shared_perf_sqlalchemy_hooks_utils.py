"""Application module for perf sqlalchemy hooks utils workflows."""

from __future__ import annotations

import re
import time

from sqlalchemy import event as sa_event

_WS_RE = re.compile(r"\s+")
_SQ_STRING_RE = re.compile(r"'(?:''|[^'])*'")
_NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_HEX_RE = re.compile(r"\b0x[0-9a-f]+\b", flags=re.IGNORECASE)
_IN_PARAMETER_RE = re.compile(
    r"\(\s*(?:\?|\$\d+|:[a-z_][a-z0-9_]*)\s*(?:,\s*(?:\?|\$\d+|:[a-z_][a-z0-9_]*)\s*)+\)",
    flags=re.IGNORECASE,
)


def normalize_sql_statement(statement: str | None) -> str:
    """Normalize sql statement."""
    normalized = (statement or "").strip().lower()
    if not normalized:
        return ""
    normalized = _SQ_STRING_RE.sub("?", normalized)
    normalized = _HEX_RE.sub("?", normalized)
    normalized = _NUMERIC_RE.sub("?", normalized)
    normalized = _IN_PARAMETER_RE.sub("(?)", normalized)
    normalized = _WS_RE.sub(" ", normalized)
    return normalized[:512]


def register_listeners(engine, *, event_impl=sa_event, perf_ctx, perf_module):
    """Attach lightweight timing hooks for DB statements."""
    sync_engine = engine.sync_engine

    @event_impl.listens_for(sync_engine, "before_cursor_execute")
    def before_cursor_execute(
        _conn, _cursor, _statement, _parameters, context, _executemany
    ):
        if not perf_module.perf_logging_enabled():
            return
        context._winoe_perf_start = time.perf_counter()
        if perf_module.perf_sql_fingerprints_enabled():
            context._winoe_perf_statement = _statement

    @event_impl.listens_for(sync_engine, "after_cursor_execute")
    def after_cursor_execute(
        _conn, _cursor, _statement, _parameters, context, _executemany
    ):
        if not perf_module.perf_logging_enabled():
            return
        start = getattr(context, "_winoe_perf_start", None)
        if start is None:
            return
        stats = perf_ctx.get()
        if stats is None:
            return
        elapsed_ms = (time.perf_counter() - start) * 1000
        stats.db_count += 1
        stats.db_time_ms += elapsed_ms
        if not perf_module.perf_sql_fingerprints_enabled():
            return
        statement = getattr(context, "_winoe_perf_statement", None)
        fingerprint = normalize_sql_statement(statement)
        stats.record_sql(fingerprint, elapsed_ms)


__all__ = ["normalize_sql_statement", "register_listeners", "sa_event"]
