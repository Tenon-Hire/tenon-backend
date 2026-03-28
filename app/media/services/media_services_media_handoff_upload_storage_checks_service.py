"""Application module for media services media handoff upload storage checks service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.config import settings
from app.integrations.storage_media import StorageMediaProvider
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.shared.utils.shared_utils_errors_utils import (
    MEDIA_STORAGE_UNAVAILABLE,
    REQUEST_TOO_LARGE,
    ApiError,
)


def load_uploaded_object_metadata(
    *, storage_provider: StorageMediaProvider, storage_key: str
):
    """Load uploaded object metadata."""
    try:
        metadata = storage_provider.get_object_metadata(storage_key)
    except StorageMediaError as exc:
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Media storage unavailable",
            error_code=MEDIA_STORAGE_UNAVAILABLE,
            retryable=True,
        ) from exc
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object not found",
        )
    return metadata


def assert_uploaded_object_matches_expected(
    *,
    expected_content_type: str,
    expected_size_bytes: int,
    actual_content_type: str,
    actual_size_bytes: int,
) -> None:
    """Assert uploaded object matches expected."""
    actual_size = int(actual_size_bytes)
    expected_size = int(expected_size_bytes)
    max_bytes = int(settings.storage_media.MEDIA_MAX_UPLOAD_BYTES)
    if actual_size > max_bytes:
        raise ApiError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded object size exceeds max {max_bytes}",
            error_code=REQUEST_TOO_LARGE,
            retryable=False,
            details={
                "field": "sizeBytes",
                "maxBytes": max_bytes,
                "actualBytes": actual_size,
            },
        )
    if actual_size != expected_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object size does not match expected size",
        )
    expected_type = normalize_content_type(expected_content_type)
    actual_type = normalize_content_type(actual_content_type)
    if actual_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded object content type does not match expected contentType",
        )


def normalize_content_type(value: str) -> str:
    """Normalize content type."""
    return (value or "").split(";", 1)[0].strip().lower()


__all__ = [
    "assert_uploaded_object_matches_expected",
    "load_uploaded_object_metadata",
    "normalize_content_type",
]
