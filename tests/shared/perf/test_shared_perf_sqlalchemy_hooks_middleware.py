import time
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.shared.utils import shared_utils_perf_utils as perf


@pytest.mark.asyncio
async def test_attach_sqlalchemy_listeners_guard(monkeypatch):
    monkeypatch.setattr(perf, "_listeners_attached", False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        perf.attach_sqlalchemy_listeners(engine)
        assert perf._listeners_attached is True
        perf.attach_sqlalchemy_listeners(engine)
    finally:
        await engine.dispose()
    perf._listeners_attached = False


def test_clear_request_stats_error_path(monkeypatch):
    class BrokenCtx:
        def reset(self, token):
            raise RuntimeError("boom")

        def set(self, value):
            self.value = value
            return value

    token = perf._start_request_stats()
    monkeypatch.setattr(perf, "_perf_ctx", BrokenCtx())
    perf._clear_request_stats(token)


def test_get_request_stats_returns_default(monkeypatch):
    monkeypatch.setattr(
        perf, "_perf_ctx", perf.ContextVar("perf_ctx_test", default=None)
    )
    stats = perf._get_request_stats()
    assert stats.db_count == 0 and stats.db_time_ms == 0


@pytest.mark.asyncio
async def test_sqlalchemy_listeners_record_stats(monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", True)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    perf.attach_sqlalchemy_listeners(engine)
    token = perf._start_request_stats()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        stats = perf._get_request_stats()
        assert stats.db_count >= 1
        assert stats.db_time_ms >= 0
    finally:
        perf._clear_request_stats(token)
        await engine.dispose()
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)


def test_sqlalchemy_listeners_early_return_paths(monkeypatch):
    captured = {}

    def fake_listens_for(_target, name):
        def decorator(fn):
            captured[name] = fn
            return fn

        return decorator

    monkeypatch.setattr(perf, "_listeners_attached", False)
    monkeypatch.setattr(perf, "event", SimpleNamespace(listens_for=fake_listens_for))
    perf.attach_sqlalchemy_listeners(SimpleNamespace(sync_engine=object()))

    ctx = SimpleNamespace()
    monkeypatch.setattr(perf, "perf_logging_enabled", lambda: False)
    captured["before_cursor_execute"](None, None, None, None, ctx, None)
    captured["after_cursor_execute"](None, None, None, None, ctx, None)

    monkeypatch.setattr(perf, "perf_logging_enabled", lambda: True)
    captured["after_cursor_execute"](None, None, None, None, SimpleNamespace(), None)

    class DummyPerfCtx:
        def get(self):
            return None

    monkeypatch.setattr(perf, "_perf_ctx", DummyPerfCtx())
    ctx_start = SimpleNamespace(_winoe_perf_start=time.perf_counter())
    captured["after_cursor_execute"](None, None, None, None, ctx_start, None)


def test_sql_normalization_reduces_literal_noise():
    normalized = perf.normalize_sql_statement(
        "SELECT * FROM tasks WHERE id = 42 AND email='Jane@Example.com'"
    )
    assert "42" not in normalized
    assert "jane@example.com" not in normalized
    assert "?" in normalized
