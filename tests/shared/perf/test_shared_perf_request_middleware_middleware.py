import logging
import re

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.shared.utils import shared_utils_perf_utils as perf


def test_request_id_from_scope_handles_invalid_bytes(monkeypatch):
    scope = {"headers": [(b"x-request-id", b"\xff")]}
    request_id = perf._request_id_from_scope(scope)
    assert request_id != "\xff"
    assert re.fullmatch(r"[a-f0-9-]{36}", request_id)


def test_request_id_from_scope_ignores_non_request_id_headers():
    scope = {"headers": [(b"x-other-header", b"value")]}
    request_id = perf._request_id_from_scope(scope)
    assert re.fullmatch(r"[a-f0-9-]{36}", request_id)


@pytest.mark.asyncio
async def test_perf_middleware_injects_request_id_and_logs(caplog, monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", True)
    monkeypatch.setattr(perf.settings, "PERF_SPANS_ENABLED", False)
    caplog.set_level(logging.INFO, logger="app.shared.perf")
    app = FastAPI()

    @app.get("/ping")
    async def _ping():
        return {"ok": True}

    app.add_middleware(perf.RequestPerfMiddleware)
    transport = ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/ping", headers={"X-Request-Id": "keep-me"})

    assert resp.status_code == 200
    assert resp.headers["x-request-id"] == "keep-me"
    record = next(r for r in caplog.records if r.message == "perf_request")
    assert record.request_id == "keep-me"
    assert record.db_count == 0
    assert perf._perf_ctx.get() is None
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)


@pytest.mark.asyncio
async def test_perf_middleware_emits_structured_spans(caplog, monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)
    monkeypatch.setattr(perf.settings, "PERF_SPANS_ENABLED", True)
    monkeypatch.setattr(perf.settings, "PERF_SPAN_SAMPLE_RATE", 1.0)
    caplog.set_level(logging.INFO, logger="app.shared.perf")
    app = FastAPI()

    @app.get("/ping")
    async def _ping():
        return {"ok": True}

    app.add_middleware(perf.RequestPerfMiddleware)
    transport = ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/ping", headers={"X-Request-Id": "span-me"})

    assert resp.status_code == 200
    record = next(r for r in caplog.records if r.message == "perf_request")
    assert record.request_span["requestId"] == "span-me"
    assert record.request_span["route"] == "/ping"
    assert record.sql_span["count"] == 0
    assert record.external_span["totalCalls"] == 0
    monkeypatch.setattr(perf.settings, "PERF_SPANS_ENABLED", False)


@pytest.mark.asyncio
async def test_perf_middleware_noop_when_debug_disabled(monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)
    monkeypatch.setattr(perf.settings, "PERF_SPANS_ENABLED", False)
    app = FastAPI()

    @app.get("/ping")
    async def _ping():
        return {"ok": True}

    app.add_middleware(perf.RequestPerfMiddleware)
    transport = ASGITransport(app=app, client=("10.0.0.1", 9999))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/ping", headers={"X-Request-Id": "noop"})

    assert resp.status_code == 200
    assert "x-request-id" not in resp.headers
