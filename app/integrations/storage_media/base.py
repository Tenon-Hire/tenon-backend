from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

_SAFE_KEY_RE = re.compile(r"^[a-z0-9/_\.\-]+$")


class StorageMediaError(RuntimeError):
    """Raised when object storage URL generation fails."""


@dataclass(frozen=True)
class StorageObjectMetadata:
    """Minimal object metadata needed to verify uploaded media."""

    content_type: str
    size_bytes: int


def clamp_expires_seconds(
    requested: int,
    *,
    min_seconds: int,
    max_seconds: int,
) -> int:
    """Bound signed URL TTL to configured limits."""
    if requested < min_seconds:
        return min_seconds
    if requested > max_seconds:
        return max_seconds
    return requested


def ensure_safe_storage_key(key: str) -> str:
    """Validate a normalized object key."""
    normalized = (key or "").strip()
    if not normalized:
        raise StorageMediaError("Storage key is required")
    if normalized.startswith("/") or normalized.startswith("\\"):
        raise StorageMediaError("Storage key must be relative")
    if "\\" in normalized:
        raise StorageMediaError("Storage key must not contain backslashes")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise StorageMediaError("Storage key path segments are invalid")
    if not _SAFE_KEY_RE.fullmatch(normalized):
        raise StorageMediaError("Storage key contains unsupported characters")
    return normalized


class StorageMediaProvider(Protocol):
    """Signed URL provider for direct media upload/download."""

    def create_signed_upload_url(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_seconds: int,
    ) -> str:
        ...

    def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
        ...

    def get_object_metadata(self, key: str) -> StorageObjectMetadata | None:
        ...

    def delete_object(self, key: str) -> None:
        ...


__all__ = [
    "StorageObjectMetadata",
    "StorageMediaError",
    "StorageMediaProvider",
    "clamp_expires_seconds",
    "ensure_safe_storage_key",
]
