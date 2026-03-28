"""Application module for integrations storage media storage media fake provider client workflows."""

from __future__ import annotations

import time
from hashlib import sha256
from urllib.parse import urlencode

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageObjectMetadata,
    ensure_safe_storage_key,
)
from app.shared.utils import shared_utils_perf_utils as perf


class FakeStorageMediaProvider:
    """Deterministic signed URL provider for tests and local development."""

    def __init__(
        self,
        *,
        base_url: str = "https://fake-storage.local",
        signing_secret: str = "fake-storage-secret",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._signing_secret = signing_secret
        self._objects: dict[str, StorageObjectMetadata] = {}

    def create_signed_upload_url(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_seconds: int,
    ) -> str:
        """Create signed upload url."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        token = self._token(
            "upload",
            safe_key,
            str(content_type),
            str(size_bytes),
            str(expires_seconds),
        )
        query = urlencode(
            {
                "key": safe_key,
                "contentType": content_type,
                "sizeBytes": size_bytes,
                "expiresIn": expires_seconds,
                "sig": token,
            }
        )
        try:
            return f"{self._base_url}/upload?{query}"
        finally:
            perf.record_external_wait(
                "storage", (time.perf_counter() - started) * 1000.0
            )

    def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
        """Create signed download url."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        token = self._token("download", safe_key, str(expires_seconds))
        query = urlencode({"key": safe_key, "expiresIn": expires_seconds, "sig": token})
        try:
            return f"{self._base_url}/download?{query}"
        finally:
            perf.record_external_wait(
                "storage", (time.perf_counter() - started) * 1000.0
            )

    def get_object_metadata(self, key: str) -> StorageObjectMetadata | None:
        """Return object metadata."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        try:
            return self._objects.get(safe_key)
        finally:
            perf.record_external_wait(
                "storage", (time.perf_counter() - started) * 1000.0
            )

    def set_object_metadata(
        self,
        key: str,
        *,
        content_type: str,
        size_bytes: int,
    ) -> None:
        """Set object metadata."""
        safe_key = ensure_safe_storage_key(key)
        normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
        self._objects[safe_key] = StorageObjectMetadata(
            content_type=normalized_content_type,
            size_bytes=int(size_bytes),
        )

    def delete_object(self, key: str) -> None:
        """Delete object."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        try:
            self._objects.pop(safe_key, None)
        finally:
            perf.record_external_wait(
                "storage", (time.perf_counter() - started) * 1000.0
            )

    def _token(self, *parts: str) -> str:
        raw = "|".join((*parts, self._signing_secret))
        return sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["FakeStorageMediaProvider"]
