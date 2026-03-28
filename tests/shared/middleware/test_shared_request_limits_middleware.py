import pytest
from fastapi import FastAPI, Request
from httpx import AsyncByteStream, AsyncClient

from app.shared.utils.shared_utils_request_limits_utils import (
    RequestSizeLimitMiddleware,
)


class ChunkStream(AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _limit_test_app(max_body_bytes: int) -> FastAPI:
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: Request):
        await request.body()
        return {"ok": True}

    app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=max_body_bytes)
    return app


@pytest.mark.asyncio
async def test_request_size_limit_blocks_large_body_with_content_length():
    app = _limit_test_app(max_body_bytes=10)
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.post("/upload", content=b"x" * 20)
    assert resp.status_code == 413
    assert resp.json()["detail"] == "Request body too large"


@pytest.mark.asyncio
async def test_request_size_limit_blocks_streaming_body_without_content_length():
    app = _limit_test_app(max_body_bytes=10)
    stream = ChunkStream([b"x" * 8, b"y" * 8])
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.post("/upload", content=stream)
    assert resp.status_code == 413
    assert resp.json()["detail"] == "Request body too large"


@pytest.mark.asyncio
async def test_request_size_limit_passes_through_non_http(monkeypatch):
    called = {"ran": False}

    async def app(scope, receive, send):
        called["ran"] = True

    middleware = RequestSizeLimitMiddleware(app, max_body_bytes=1)
    await middleware({"type": "lifespan"}, lambda: None, lambda _m: None)
    assert called["ran"] is True


@pytest.mark.asyncio
async def test_request_size_limit_ignores_non_request_messages():
    sent: list[dict] = []
    received_messages: list[dict] = []

    async def app(scope, receive, send):
        received_messages.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestSizeLimitMiddleware(app, max_body_bytes=1)
    messages = iter([{"type": "http.disconnect"}])

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    await middleware(
        {"type": "http", "method": "POST", "headers": []},
        receive,
        send,
    )

    assert received_messages == [{"type": "http.disconnect"}]
    assert sent[0]["status"] == 200
