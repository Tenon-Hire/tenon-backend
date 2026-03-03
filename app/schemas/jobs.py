from __future__ import annotations

from typing import Any

from app.domains.common.base import APIModel


class JobStatusResponse(APIModel):
    """Public job status payload for polling."""

    jobId: str
    jobType: str
    status: str
    attempt: int
    maxAttempts: int
    pollAfterMs: int
    result: dict[str, Any] | None
    error: str | None
