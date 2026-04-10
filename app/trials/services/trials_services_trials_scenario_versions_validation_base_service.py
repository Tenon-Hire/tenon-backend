"""Application module for trials services trials scenario versions validation base service workflows."""

from __future__ import annotations

import json
from typing import Any

from fastapi import status

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)
from app.trials.schemas.trials_schemas_trials_core_schema import (
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_STORYLINE_CHARS,
)
from app.trials.services.trials_services_trials_scenario_versions_constants import (
    SCENARIO_PATCH_ERROR_CODE,
)


def json_payload_size_bytes(value: Any) -> int:
    """Execute json payload size bytes."""
    encoded = json.dumps(
        value,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return len(encoded)


def parse_positive_int(value: Any) -> int | None:
    """Parse positive int."""
    return _parse_positive_int_value(value, strip_strings=True)


def raise_patch_validation_error(
    detail: str, *, field: str | None = None, details: dict[str, Any] | None = None
) -> None:
    """Execute raise patch validation error."""
    payload_details = dict(details or {})
    if field is not None:
        payload_details["field"] = field
    raise ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
        error_code=SCENARIO_PATCH_ERROR_CODE,
        retryable=False,
        details=payload_details,
    )


def validate_storyline(storyline_md: Any) -> str:
    """Validate storyline."""
    if not isinstance(storyline_md, str):
        raise_patch_validation_error(
            "storylineMd must be a string.",
            field="storylineMd",
        )
    if len(storyline_md) > MAX_SCENARIO_STORYLINE_CHARS:
        raise_patch_validation_error(
            f"storylineMd exceeds {MAX_SCENARIO_STORYLINE_CHARS} characters.",
            field="storylineMd",
            details={
                "maxChars": MAX_SCENARIO_STORYLINE_CHARS,
                "actualChars": len(storyline_md),
            },
        )
    return storyline_md


def validate_notes(notes: Any) -> str:
    """Validate notes."""
    if not isinstance(notes, str):
        raise_patch_validation_error(
            "notes must be a string.",
            field="notes",
        )
    if len(notes) > MAX_SCENARIO_NOTES_CHARS:
        raise_patch_validation_error(
            f"notes exceeds {MAX_SCENARIO_NOTES_CHARS} characters.",
            field="notes",
            details={
                "maxChars": MAX_SCENARIO_NOTES_CHARS,
                "actualChars": len(notes),
            },
        )
    return notes
