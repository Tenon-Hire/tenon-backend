from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.core.errors import ApiError


def api_error_handler(_request, exc: ApiError) -> JSONResponse:
    payload: dict[str, Any] = {
        "detail": exc.detail,
        "errorCode": exc.error_code,
        "retryable": exc.retryable if exc.retryable is not None else False,
        "details": exc.details or {},
    }
    return JSONResponse(
        status_code=exc.status_code, content=payload, headers=exc.headers
    )


__all__ = ["api_error_handler"]
