import logging
import re

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.infra import perf


def test_request_id_from_scope_handles_invalid_bytes(monkeypatch):
    # Invalid header bytes should fall back to a generated UUID instead of crashing.
    scope = {"headers": [(b"x-request-id", b"\xff")]}
    request_id = perf._request_id_from_scope(scope)
    assert request_id != "\xff"
    assert re.fullmatch(r"[a-f0-9-]{36}", request_id)


@pytest.mark.asyncio
async def test_perf_middleware_injects_request_id_and_logs(caplog, monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", True)
    caplog.set_level(logging.INFO, logger="app.infra.perf")

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
    # Context var should be cleared after request.
    assert perf._perf_ctx.get() is None
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)


@pytest.mark.asyncio
async def test_perf_middleware_noop_when_debug_disabled(monkeypatch):
    monkeypatch.setattr(perf.settings, "DEBUG_PERF", False)
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


@pytest.mark.asyncio
async def test_attach_sqlalchemy_listeners_guard(monkeypatch):
    monkeypatch.setattr(perf, "_listeners_attached", False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        perf.attach_sqlalchemy_listeners(engine)
        assert perf._listeners_attached is True
        # Subsequent calls should be no-ops and not raise.
        perf.attach_sqlalchemy_listeners(engine)
    finally:
        await engine.dispose()
    # Reset for other tests that may rely on defaults.
    perf._listeners_attached = False
