from __future__ import annotations

from typing import Any, Final

from fastapi import HTTPException

CANDIDATE_EMAIL_NOT_VERIFIED: Final[str] = "CANDIDATE_EMAIL_NOT_VERIFIED"
CANDIDATE_INVITE_EMAIL_MISMATCH: Final[str] = "CANDIDATE_INVITE_EMAIL_MISMATCH"
CANDIDATE_AUTH_EMAIL_MISSING: Final[str] = "CANDIDATE_AUTH_EMAIL_MISSING"
CANDIDATE_SESSION_ALREADY_CLAIMED: Final[str] = "CANDIDATE_SESSION_ALREADY_CLAIMED"


class ApiError(HTTPException):
    """HTTP error with a stable error code and optional metadata."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        error_code: str,
        retryable: bool | None = None,
        headers: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.retryable = retryable
        self.details = details or {}


__all__ = [
    "ApiError",
    "CANDIDATE_EMAIL_NOT_VERIFIED",
    "CANDIDATE_INVITE_EMAIL_MISMATCH",
    "CANDIDATE_AUTH_EMAIL_MISSING",
    "CANDIDATE_SESSION_ALREADY_CLAIMED",
]
