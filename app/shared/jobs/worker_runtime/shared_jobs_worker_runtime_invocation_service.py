"""Application module for jobs worker runtime invocation service workflows."""

from __future__ import annotations

import inspect
from typing import Any

from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    JobHandler,
    PermanentJobError,
)


async def invoke_handler(
    handler: JobHandler, payload_json: dict[str, Any]
) -> dict[str, Any] | None:
    """Execute invoke handler."""
    value = handler(payload_json)
    if inspect.isawaitable(value):
        value = await value
    if value is not None and not isinstance(value, dict):
        raise PermanentJobError("job handler result must be a JSON object or null")
    return value


__all__ = ["invoke_handler"]
