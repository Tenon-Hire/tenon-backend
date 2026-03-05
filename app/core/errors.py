from __future__ import annotations

from typing import Any, Final

from fastapi import HTTPException

CANDIDATE_EMAIL_NOT_VERIFIED: Final[str] = "CANDIDATE_EMAIL_NOT_VERIFIED"
CANDIDATE_INVITE_EMAIL_MISMATCH: Final[str] = "CANDIDATE_INVITE_EMAIL_MISMATCH"
CANDIDATE_AUTH_EMAIL_MISSING: Final[str] = "CANDIDATE_AUTH_EMAIL_MISSING"
CANDIDATE_SESSION_ALREADY_CLAIMED: Final[str] = "CANDIDATE_SESSION_ALREADY_CLAIMED"
INVITE_TOKEN_EXPIRED: Final[str] = "INVITE_TOKEN_EXPIRED"
SCHEDULE_ALREADY_SET: Final[str] = "SCHEDULE_ALREADY_SET"
SCHEDULE_INVALID_TIMEZONE: Final[str] = "SCHEDULE_INVALID_TIMEZONE"
SCHEDULE_START_IN_PAST: Final[str] = "SCHEDULE_START_IN_PAST"
SCHEDULE_NOT_CLAIMED: Final[str] = "SCHEDULE_NOT_CLAIMED"
SCHEDULE_INVALID_WINDOW: Final[str] = "SCHEDULE_INVALID_WINDOW"
SCHEDULE_NOT_STARTED: Final[str] = "SCHEDULE_NOT_STARTED"


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
    "INVITE_TOKEN_EXPIRED",
    "SCHEDULE_ALREADY_SET",
    "SCHEDULE_INVALID_TIMEZONE",
    "SCHEDULE_START_IN_PAST",
    "SCHEDULE_NOT_CLAIMED",
    "SCHEDULE_INVALID_WINDOW",
    "SCHEDULE_NOT_STARTED",
]
