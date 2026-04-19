"""Application module for submissions services submissions payload validation service workflows."""

from __future__ import annotations

import logging
from collections import Counter

from fastapi import HTTPException, status

from app.shared.database.shared_database_models_model import Task
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    SubmissionValidationError,
)

TEXT_TASK_TYPES = {"design", "documentation", "handoff"}
CODE_TASK_TYPES = {"code", "debug"}
DAY5_REFLECTION_TASK_TYPE = "documentation"
DAY5_REFLECTION_DAY_INDEX = 5
DAY5_REFLECTION_KIND = "day5_reflection"
DAY5_REFLECTION_MIN_SECTION_CHARS = 20
DAY5_REFLECTION_SECTIONS = (
    "challenges",
    "decisions",
    "tradeoffs",
    "communication",
    "next",
)

logger = logging.getLogger(__name__)


def is_code_task(task: Task) -> bool:
    """Return True if the task requires code."""
    return (task.type or "").lower() in CODE_TASK_TYPES


def is_day5_reflection_task(task: Task) -> bool:
    """Return True when the task is the Day 5 reflection task."""
    return (task.type or "").lower() == DAY5_REFLECTION_TASK_TYPE and (
        getattr(task, "day_index", None) == DAY5_REFLECTION_DAY_INDEX
    )


def _require_content_text(payload) -> None:
    _, error_code = _resolve_content_text_value(payload)
    if error_code is None:
        return
    if error_code == "invalid_type":
        detail = "contentText must be a string"
    else:
        detail = "contentText is required"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def _resolve_content_text_value(payload) -> tuple[str | None, str | None]:
    content_text = getattr(payload, "contentText", None)
    if content_text is None:
        return None, "missing"
    if not isinstance(content_text, str):
        return None, "invalid_type"
    normalized = content_text.strip()
    if not normalized:
        return None, "missing"
    return normalized, None


def _require_content_text_value(payload) -> str:
    content_text, error_code = _resolve_content_text_value(payload)
    if error_code is None and content_text is not None:
        return content_text
    if error_code == "invalid_type":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contentText must be a string",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="contentText is required",
    )


def _log_day5_validation_failure(fields: dict[str, list[str]]) -> None:
    counts = Counter()
    for codes in fields.values():
        counts.update(codes)
    logger.info(
        "Day5 reflection validation failed missing=%s too_short=%s invalid_type=%s fieldCount=%s",
        counts.get("missing", 0),
        counts.get("too_short", 0),
        counts.get("invalid_type", 0),
        len(fields),
    )


def _validate_day5_reflection_payload(payload) -> dict[str, object]:
    fields: dict[str, list[str]] = {}
    content_text, content_text_error = _resolve_content_text_value(payload)
    if content_text_error is not None:
        fields["contentText"] = [content_text_error]
    reflection_payload = getattr(payload, "reflection", None)
    if reflection_payload is None:
        if fields:
            _log_day5_validation_failure(fields)
            raise SubmissionValidationError(fields=fields)
        return {"kind": DAY5_REFLECTION_KIND, "markdown": content_text}
    reflection: dict[str, object] = {}
    if not isinstance(reflection_payload, dict):
        fields["reflection"] = ["invalid_type"]
    else:
        reflection = reflection_payload

    sections: dict[str, str] = {}
    for section in DAY5_REFLECTION_SECTIONS:
        field_key = f"reflection.{section}"
        raw_value = reflection.get(section)
        if raw_value is None:
            fields[field_key] = ["missing"]
            continue
        if not isinstance(raw_value, str):
            fields[field_key] = ["invalid_type"]
            continue
        normalized = raw_value.strip()
        if not normalized:
            fields[field_key] = ["missing"]
            continue
        if len(normalized) < DAY5_REFLECTION_MIN_SECTION_CHARS:
            fields[field_key] = ["too_short"]
            continue
        sections[section] = normalized

    if fields:
        _log_day5_validation_failure(fields)
        raise SubmissionValidationError(fields=fields)

    return {
        "kind": DAY5_REFLECTION_KIND,
        "markdown": content_text,
        "sections": sections,
    }


def validate_submission_payload(task: Task, payload) -> dict[str, object] | None:
    """Validate submission payload for non-code tasks."""
    task_type = (task.type or "").lower()
    if task_type in TEXT_TASK_TYPES:
        if is_day5_reflection_task(task):
            return _validate_day5_reflection_payload(payload)
        _require_content_text(payload)
        return None
    if task_type in CODE_TASK_TYPES:
        return None
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unknown task type",
    )


def validate_run_allowed(task: Task) -> None:
    """Run tests only applies to code tasks."""
    if not is_code_task(task):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run tests is only available for code tasks",
        )
