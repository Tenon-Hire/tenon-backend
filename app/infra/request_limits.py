from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse

from app.infra.config import settings


class RequestTooLarge(Exception):
    """Raised when request body exceeds configured size limit."""


class RequestSizeLimitMiddleware:
    """Reject requests with payloads larger than the configured limit."""

    def __init__(self, app, max_body_bytes: int | None = None) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes or settings.MAX_REQUEST_BODY_BYTES

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length", b"").decode("latin1").strip()
        if content_length.isdigit() and int(content_length) > self.max_body_bytes:
            response = JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"},
            )
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                received += len(body)
                if received > self.max_body_bytes:
                    raise RequestTooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            response = JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"},
            )
            await response(scope, receive, send)
