"""Application module for perf middleware workflows."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.types import ASGIApp, Receive, Scope, Send

from .shared_perf_config import perf_logging_enabled
from .shared_perf_context_utils import (
    clear_request_stats,
    get_request_stats,
    start_request_stats,
)
from .shared_perf_middleware_spans_middleware import (
    external_span_payload,
    request_span_payload,
    sample_perf_span,
    sql_span_payload,
)
from .shared_perf_request_id_utils import request_id_from_scope

logger = logging.getLogger(__name__)


def create_request_perf_middleware(get_perf_ctx: Callable[[], object]):
    """Create request perf middleware."""

    class RequestPerfMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope.get("type") != "http" or not perf_logging_enabled():
                await self.app(scope, receive, send)
                return
            perf_ctx = get_perf_ctx()
            token = start_request_stats(perf_ctx)
            request_id = request_id_from_scope(scope)
            status_code = 500
            response_bytes = 0
            started = time.perf_counter()

            async def send_wrapper(message):
                nonlocal status_code, response_bytes
                if message["type"] == "http.response.start":
                    status_code = message.get("status", status_code)
                    headers = [
                        (k, v)
                        for (k, v) in message.get("headers", [])
                        if k.lower() != b"x-request-id"
                    ]
                    headers.append((b"x-request-id", request_id.encode()))
                    message["headers"] = headers
                elif message["type"] == "http.response.body":
                    response_bytes += len(message.get("body") or b"")
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                duration_ms = (time.perf_counter() - started) * 1000
                stats = get_request_stats(perf_ctx)
                route = scope.get("route")
                path_template = (
                    getattr(route, "path", None)
                    or getattr(route, "path_format", None)
                    or scope.get("path")
                )
                extra = {
                    "method": scope.get("method"),
                    "path_template": path_template,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 3),
                    "db_count": stats.db_count,
                    "db_time_ms": round(stats.db_time_ms, 3),
                    "response_bytes": response_bytes,
                    "request_id": request_id,
                }
                if sample_perf_span():
                    extra["request_span"] = request_span_payload(
                        request_id=request_id,
                        method=scope.get("method"),
                        path_template=path_template,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        response_bytes=response_bytes,
                    )
                    extra["sql_span"] = sql_span_payload(stats)
                    extra["external_span"] = external_span_payload(stats)
                logger.info("perf_request", extra=extra)
                clear_request_stats(perf_ctx, token)

    return RequestPerfMiddleware


_request_id_from_scope = request_id_from_scope
__all__ = ["create_request_perf_middleware", "_request_id_from_scope"]
