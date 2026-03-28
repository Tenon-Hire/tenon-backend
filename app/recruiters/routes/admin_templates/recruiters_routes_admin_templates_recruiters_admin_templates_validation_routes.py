"""Application module for recruiters routes admin templates recruiters admin templates validation routes workflows."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    TemplateKeyError,
    validate_template_key,
)

MAX_LIVE_TEMPLATE_KEYS = 5


def validate_live_request(payload) -> tuple[list[str], int, int]:
    """Validate live request."""
    if payload.mode != "live":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only live mode is supported for this endpoint",
        )
    if not payload.templateKeys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="templateKeys is required",
        )
    if len(payload.templateKeys) > MAX_LIVE_TEMPLATE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"templateKeys must include {MAX_LIVE_TEMPLATE_KEYS} or fewer items",
        )
    template_keys: list[str] = []
    invalid: list[str] = []
    for key in payload.templateKeys:
        try:
            template_keys.append(validate_template_key(key))
        except TemplateKeyError:
            invalid.append(key)
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid templateKeys: {', '.join(invalid)}",
        )
    timeout_seconds = max(1, min(payload.timeoutSeconds, 600))
    concurrency = max(1, min(payload.concurrency, 5))
    return template_keys, timeout_seconds, concurrency
