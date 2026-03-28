"""Application module for http middleware http csrf middleware workflows."""

from __future__ import annotations

import logging

from fastapi import status
from fastapi.responses import JSONResponse

from .shared_http_middleware_http_config import _normalize_path_prefix
from .shared_http_middleware_http_request_middleware import (
    _headers_map,
    _is_cookie_authenticated_request,
    _normalize_origin,
    _path_matches_prefixes,
)

_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_ORIGIN_MISMATCH_RESPONSE = {
    "error": "CSRF_ORIGIN_MISMATCH",
    "message": "Request origin not allowed.",
}
logger = logging.getLogger("app.shared.http.shared_http_middleware_http_middleware")


class CsrfOriginEnforcementMiddleware:
    """Represent csrf origin enforcement middleware data and behavior."""

    def __init__(
        self,
        app,
        *,
        allowed_origins: list[str] | None = None,
        protected_path_prefixes: list[str] | None = None,
    ) -> None:
        self.app = app
        self.allowed_origins = {
            normalized
            for origin in (allowed_origins or [])
            if (normalized := _normalize_origin(origin))
        }
        self.protected_path_prefixes = [
            prefix
            for prefix in (
                _normalize_path_prefix(p) for p in (protected_path_prefixes or [])
            )
            if prefix
        ]

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        method = str(scope.get("method") or "").upper()
        path = str(scope.get("path") or "")
        if method not in _STATE_CHANGING_METHODS:
            await self.app(scope, receive, send)
            return
        if not _path_matches_prefixes(path, self.protected_path_prefixes):
            await self.app(scope, receive, send)
            return
        headers = _headers_map(scope.get("headers") or [])
        if not _is_cookie_authenticated_request(headers):
            await self.app(scope, receive, send)
            return

        raw_origin = (headers.get("origin") or "").strip()
        raw_referer = (headers.get("referer") or "").strip()
        origin = _normalize_origin(raw_origin) if raw_origin else None
        referer_origin = _normalize_origin(raw_referer) if raw_referer else None
        observed_origin = origin if raw_origin else referer_origin
        if observed_origin in self.allowed_origins:
            await self.app(scope, receive, send)
            return

        logger.warning(
            "csrf_origin_mismatch",
            extra={
                "method": method,
                "path": path,
                "origin": raw_origin or None,
                "referer_origin": referer_origin,
            },
        )
        response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=dict(_CSRF_ORIGIN_MISMATCH_RESPONSE),
        )
        await response(scope, receive, send)
