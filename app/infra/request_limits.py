from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.infra.config import settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with payloads larger than the configured limit."""

    def __init__(self, app, max_body_bytes: int | None = None) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes or settings.MAX_REQUEST_BODY_BYTES

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length = (request.headers.get("content-length") or "").strip()
            if content_length.isdigit():
                if int(content_length) > self.max_body_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Request body too large"},
                    )
            body = await request.body()
            if len(body) > self.max_body_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large"},
                )
        return await call_next(request)
