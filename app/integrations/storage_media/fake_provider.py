from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlencode

from app.integrations.storage_media.base import (
    StorageObjectMetadata,
    ensure_safe_storage_key,
)


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
        return f"{self._base_url}/upload?{query}"

    def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
        safe_key = ensure_safe_storage_key(key)
        token = self._token("download", safe_key, str(expires_seconds))
        query = urlencode({"key": safe_key, "expiresIn": expires_seconds, "sig": token})
        return f"{self._base_url}/download?{query}"

    def get_object_metadata(self, key: str) -> StorageObjectMetadata | None:
        safe_key = ensure_safe_storage_key(key)
        return self._objects.get(safe_key)

    def set_object_metadata(
        self,
        key: str,
        *,
        content_type: str,
        size_bytes: int,
    ) -> None:
        safe_key = ensure_safe_storage_key(key)
        normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
        self._objects[safe_key] = StorageObjectMetadata(
            content_type=normalized_content_type,
            size_bytes=int(size_bytes),
        )

    def delete_object(self, key: str) -> None:
        safe_key = ensure_safe_storage_key(key)
        self._objects.pop(safe_key, None)

    def _token(self, *parts: str) -> str:
        raw = "|".join((*parts, self._signing_secret))
        return sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["FakeStorageMediaProvider"]
