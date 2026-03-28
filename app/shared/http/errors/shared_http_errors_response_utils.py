"""Application module for http errors response utils workflows."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.shared.utils.shared_utils_errors_utils import ApiError


def api_error_handler(_request, exc: ApiError) -> JSONResponse:
    """Execute api error handler."""
    payload: dict[str, Any] = {"detail": exc.detail, "errorCode": exc.error_code}
    if not exc.compact_response:
        payload["retryable"] = exc.retryable if exc.retryable is not None else False
        payload["details"] = exc.details or {}
    return JSONResponse(
        status_code=exc.status_code, content=payload, headers=exc.headers
    )


__all__ = ["api_error_handler"]
