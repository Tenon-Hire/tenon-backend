from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Request


def make_request(headers: dict[str, str], host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 1234),
        "path": "/",
        "method": "GET",
        "query_string": b"",
        "server": ("test", 80),
    }

    async def _receive():
        return {"type": "http.request"}

    return Request(scope, _receive)


def ctx_maker(session):
    @asynccontextmanager
    async def maker():
        yield session

    return maker
