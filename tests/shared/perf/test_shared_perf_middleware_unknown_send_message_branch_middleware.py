from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.perf import shared_perf_middleware as perf_middleware


@pytest.mark.asyncio
async def test_request_perf_middleware_passes_through_non_body_send_messages(
    monkeypatch,
):
    sent: list[dict] = []
    logged: list[dict] = []
    cleared: list[object] = []

    async def app(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.trailers", "headers": []})
        await send({"type": "http.response.body", "body": b""})

    monkeypatch.setattr(perf_middleware, "perf_logging_enabled", lambda: True)
    monkeypatch.setattr(perf_middleware, "sample_perf_span", lambda: False)
    monkeypatch.setattr(
        perf_middleware, "request_id_from_scope", lambda _scope: "req-1"
    )
    monkeypatch.setattr(
        perf_middleware,
        "start_request_stats",
        lambda _ctx: "token-1",
    )
    monkeypatch.setattr(
        perf_middleware,
        "get_request_stats",
        lambda _ctx: SimpleNamespace(db_count=0, db_time_ms=0.0),
    )
    monkeypatch.setattr(
        perf_middleware,
        "clear_request_stats",
        lambda _ctx, token: cleared.append(token),
    )
    monkeypatch.setattr(
        perf_middleware,
        "logger",
        SimpleNamespace(info=lambda _msg, *, extra: logged.append(extra)),
    )

    middleware_cls = perf_middleware.create_request_perf_middleware(lambda: object())
    middleware = middleware_cls(app)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(
        {"type": "http", "method": "GET", "path": "/ping", "headers": []},
        receive,
        send,
    )

    assert any(message["type"] == "http.response.trailers" for message in sent)
    assert logged
    assert cleared == ["token-1"]
