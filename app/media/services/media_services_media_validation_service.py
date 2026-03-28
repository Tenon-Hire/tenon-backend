"""Application module for media services media validation service workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings
from app.media.services.media_services_media_keys_service import normalize_extension
from app.shared.utils.shared_utils_errors_utils import REQUEST_TOO_LARGE, ApiError

DEFAULT_EXTENSION_BY_CONTENT_TYPE = {
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
}


@dataclass(frozen=True)
class UploadInput:
    """Represent upload input data and behavior."""

    content_type: str
    size_bytes: int
    extension: str


def validate_upload_input(
    *,
    content_type: str,
    size_bytes: int,
    filename: str | None = None,
) -> UploadInput:
    """Validate upload metadata against media settings."""
    cfg = settings.storage_media
    allowed_types = {
        str(item).strip().lower()
        for item in (cfg.MEDIA_ALLOWED_CONTENT_TYPES or [])
        if str(item).strip()
    }
    allowed_extensions = {
        str(item).strip().lower().lstrip(".")
        for item in (cfg.MEDIA_ALLOWED_EXTENSIONS or [])
        if str(item).strip()
    }

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if not normalized_type or normalized_type not in allowed_types:
        raise _unprocessable("Unsupported contentType")

    max_bytes = int(cfg.MEDIA_MAX_UPLOAD_BYTES)
    if size_bytes <= 0:
        raise _unprocessable("sizeBytes must be greater than 0")
    if size_bytes > max_bytes:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"sizeBytes exceeds max {max_bytes}",
            error_code=REQUEST_TOO_LARGE,
            retryable=False,
            details={
                "field": "sizeBytes",
                "maxBytes": max_bytes,
                "actualBytes": int(size_bytes),
            },
        )

    extension = _resolve_extension(
        content_type=normalized_type,
        filename=filename,
        allowed_extensions=allowed_extensions,
    )
    return UploadInput(
        content_type=normalized_type,
        size_bytes=size_bytes,
        extension=extension,
    )


def _resolve_extension(
    *,
    content_type: str,
    filename: str | None,
    allowed_extensions: set[str],
) -> str:
    if filename:
        extension = Path(filename).suffix.lower().lstrip(".")
        if not extension:
            raise _unprocessable("filename must include an extension")
        normalized = normalize_extension(extension)
        if normalized not in allowed_extensions:
            raise _unprocessable("Unsupported file extension")
        return normalized

    mapped = DEFAULT_EXTENSION_BY_CONTENT_TYPE.get(content_type)
    if not mapped:
        raise _unprocessable("Unable to infer extension from contentType")
    normalized = normalize_extension(mapped)
    if normalized not in allowed_extensions:
        raise _unprocessable("Unsupported file extension")
    return normalized


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
    )


__all__ = ["DEFAULT_EXTENSION_BY_CONTENT_TYPE", "UploadInput", "validate_upload_input"]
