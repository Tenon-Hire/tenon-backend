from __future__ import annotations

from typing import Any


def build_log_extra(job: Any) -> dict[str, Any]:
    return {
        "jobId": job.id,
        "jobType": job.job_type,
        "attempt": job.attempt,
        "correlation_id": job.correlation_id,
    }


def format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


__all__ = ["build_log_extra", "format_error"]
