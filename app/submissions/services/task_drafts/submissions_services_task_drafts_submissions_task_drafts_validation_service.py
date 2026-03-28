"""Application module for submissions services task drafts submissions task drafts validation service workflows."""

from __future__ import annotations

import json
from typing import Any

from fastapi import status

from app.shared.utils.shared_utils_errors_utils import DRAFT_CONTENT_TOO_LARGE, ApiError

MAX_DRAFT_CONTENT_BYTES = 200 * 1024


def utf8_size(value: str | None) -> int:
    """Execute utf8 size."""
    if value is None:
        return 0
    return len(value.encode("utf-8"))


def json_size(value: dict[str, Any] | None) -> int:
    """Execute json size."""
    if value is None:
        return 0
    encoded = json.dumps(
        value,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return len(encoded)


def validate_draft_payload_size(
    *,
    content_text: str | None,
    content_json: dict[str, Any] | None,
) -> tuple[int, int]:
    """Validate draft payload size."""
    text_bytes = utf8_size(content_text)
    json_bytes = json_size(content_json)

    if text_bytes > MAX_DRAFT_CONTENT_BYTES:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"contentText exceeds {MAX_DRAFT_CONTENT_BYTES} bytes.",
            error_code=DRAFT_CONTENT_TOO_LARGE,
            retryable=False,
            details={
                "field": "contentText",
                "maxBytes": MAX_DRAFT_CONTENT_BYTES,
                "actualBytes": text_bytes,
            },
        )

    if json_bytes > MAX_DRAFT_CONTENT_BYTES:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"contentJson exceeds {MAX_DRAFT_CONTENT_BYTES} bytes.",
            error_code=DRAFT_CONTENT_TOO_LARGE,
            retryable=False,
            details={
                "field": "contentJson",
                "maxBytes": MAX_DRAFT_CONTENT_BYTES,
                "actualBytes": json_bytes,
            },
        )

    return text_bytes, json_bytes


__all__ = [
    "MAX_DRAFT_CONTENT_BYTES",
    "utf8_size",
    "json_size",
    "validate_draft_payload_size",
]
