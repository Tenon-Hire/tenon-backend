"""Application module for simulations services simulations template keys service workflows."""

from __future__ import annotations

from fastapi import status

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    ALLOWED_TEMPLATE_KEYS,
    DEFAULT_TEMPLATE_KEY,
    TemplateKeyError,
    validate_template_key,
)


def resolve_template_key(payload) -> str:
    """Resolve template key."""
    try:
        return validate_template_key(
            getattr(payload, "templateKey", DEFAULT_TEMPLATE_KEY)
            or DEFAULT_TEMPLATE_KEY
        )
    except TemplateKeyError as exc:
        allowed = sorted(ALLOWED_TEMPLATE_KEYS)
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid templateKey. Allowed: " + ", ".join(allowed),
            error_code="INVALID_TEMPLATE_KEY",
            details={"allowed": allowed},
        ) from exc
