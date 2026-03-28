"""Application module for media services media keys service workflows."""

from __future__ import annotations

import re
import uuid

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    ensure_safe_storage_key,
)

_EXTENSION_RE = re.compile(r"^[a-z0-9]+$")
_RECORDING_ID_RE = re.compile(r"^rec_(\d+)$")


def recording_public_id(recording_id: int) -> str:
    """Convert internal integer id to API contract id."""
    return f"rec_{recording_id}"


def parse_recording_public_id(value: str) -> int:
    """Parse API contract recording id into internal integer id."""
    candidate = (value or "").strip()
    if candidate.isdigit():
        parsed = int(candidate)
        if parsed > 0:
            return parsed
    match = _RECORDING_ID_RE.fullmatch(candidate)
    if not match:
        raise ValueError("recordingId must be a positive integer or rec_<id>")
    parsed = int(match.group(1))
    if parsed <= 0:
        raise ValueError("recordingId must be positive")
    return parsed


def normalize_extension(extension: str) -> str:
    """Normalize extension."""
    normalized = (extension or "").strip().lower().lstrip(".")
    if not normalized:
        raise ValueError("File extension is required")
    if not _EXTENSION_RE.fullmatch(normalized):
        raise ValueError("Invalid file extension")
    return normalized


def build_recording_storage_key(
    *,
    candidate_session_id: int,
    task_id: int,
    extension: str,
    recording_uuid: str | None = None,
) -> str:
    """Build a namespaced, traversal-safe object key."""
    if candidate_session_id <= 0 or task_id <= 0:
        raise ValueError("candidate_session_id and task_id must be positive")
    ext = normalize_extension(extension)
    opaque = recording_uuid or uuid.uuid4().hex
    key = (
        f"candidate-sessions/{candidate_session_id}/tasks/{task_id}/"
        f"recordings/{opaque}.{ext}"
    )
    return ensure_safe_storage_key(key)


__all__ = [
    "build_recording_storage_key",
    "normalize_extension",
    "parse_recording_public_id",
    "recording_public_id",
]
