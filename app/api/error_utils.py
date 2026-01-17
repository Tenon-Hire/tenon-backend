from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.domains.github_native.client import GithubError


class ApiError(HTTPException):
    """HTTP error with a stable error code + optional retryable flag."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        error_code: str,
        retryable: bool | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.retryable = retryable


def api_error_handler(_request, exc: ApiError) -> JSONResponse:
    """Return a consistent JSON shape for ApiError."""
    payload: dict[str, Any] = {"detail": exc.detail, "errorCode": exc.error_code}
    if exc.retryable is not None:
        payload["retryable"] = exc.retryable
    return JSONResponse(
        status_code=exc.status_code, content=payload, headers=exc.headers
    )


def register_error_handlers(app) -> None:
    """Attach ApiError handler to the FastAPI app."""
    app.add_exception_handler(ApiError, api_error_handler)


def map_github_error(exc: GithubError) -> ApiError:
    """Return a safe ApiError for GitHub API failures."""
    code = exc.status_code or 0
    detail = "GitHub unavailable. Please try again."
    error_code = "GITHUB_UNAVAILABLE"
    retryable = False
    if code in {401, 403}:
        detail = "GitHub credentials are invalid or missing permissions."
        error_code = "GITHUB_PERMISSION_DENIED"
    elif code == 404:
        detail = "GitHub repository or workflow not found."
        error_code = "GITHUB_NOT_FOUND"
    elif code == 429:
        detail = "GitHub rate limit exceeded. Please retry later."
        error_code = "GITHUB_RATE_LIMITED"
        retryable = True
    return ApiError(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
        error_code=error_code,
        retryable=retryable,
    )
