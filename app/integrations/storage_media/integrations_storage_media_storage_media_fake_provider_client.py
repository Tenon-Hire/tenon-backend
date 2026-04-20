"""Application module for integrations storage media storage media fake provider client workflows."""

from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
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
        root_dir: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._signing_secret = signing_secret
        self._root_dir = Path(root_dir).expanduser() if root_dir else None
        self._objects: dict[str, StorageObjectMetadata] = {}

    def create_signed_upload_url(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_seconds: int,
        duration_seconds: int | None = None,
    ) -> str:
        """Create signed upload url."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        expires_at = int(time.time()) + int(expires_seconds)
        token = self._token(
            "upload",
            safe_key,
            str(content_type),
            str(size_bytes),
            str(expires_at),
            str(int(duration_seconds)) if duration_seconds is not None else "",
        )
        query = urlencode(
            {
                "key": safe_key,
                "contentType": content_type,
                "sizeBytes": size_bytes,
                "expiresIn": expires_seconds,
                "expiresAt": expires_at,
                "sig": token,
                **(
                    {"durationSeconds": int(duration_seconds)}
                    if duration_seconds is not None
                    else {}
                ),
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
        expires_at = int(time.time()) + int(expires_seconds)
        token = self._token("download", safe_key, str(expires_at))
        query = urlencode(
            {
                "key": safe_key,
                "expiresIn": expires_seconds,
                "expiresAt": expires_at,
                "sig": token,
            }
        )
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
            disk_metadata = self._read_disk_metadata(safe_key)
            if disk_metadata is not None:
                return disk_metadata
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
        duration_seconds: int | None = None,
    ) -> None:
        """Set object metadata."""
        safe_key = ensure_safe_storage_key(key)
        normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
        metadata = StorageObjectMetadata(
            content_type=normalized_content_type,
            size_bytes=int(size_bytes),
            duration_seconds=(
                int(duration_seconds) if duration_seconds is not None else 600
            ),
        )
        self._objects[safe_key] = metadata
        self._write_disk_metadata(safe_key, metadata)

    def delete_object(self, key: str) -> None:
        """Delete object."""
        started = time.perf_counter()
        safe_key = ensure_safe_storage_key(key)
        try:
            self._objects.pop(safe_key, None)
            self._delete_disk_object(safe_key)
        finally:
            perf.record_external_wait(
                "storage", (time.perf_counter() - started) * 1000.0
            )

    def validate_signed_upload_request(
        self,
        *,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_at: int,
        signature: str,
        duration_seconds: int | None = None,
    ) -> str:
        """Validate signed upload request and return safe key."""
        safe_key = ensure_safe_storage_key(key)
        self._validate_expiry(expires_at)
        expected = self._token(
            "upload",
            safe_key,
            str(content_type),
            str(int(size_bytes)),
            str(int(expires_at)),
            str(int(duration_seconds)) if duration_seconds is not None else "",
        )
        if signature != expected:
            raise StorageMediaError("Invalid upload signature")
        return safe_key

    def validate_signed_download_request(
        self,
        *,
        key: str,
        expires_at: int,
        signature: str,
    ) -> str:
        """Validate signed download request and return safe key."""
        safe_key = ensure_safe_storage_key(key)
        self._validate_expiry(expires_at)
        expected = self._token("download", safe_key, str(int(expires_at)))
        if signature != expected:
            raise StorageMediaError("Invalid download signature")
        return safe_key

    def write_object_bytes(
        self,
        key: str,
        *,
        content_type: str,
        data: bytes,
        duration_seconds: int | None = None,
    ) -> StorageObjectMetadata:
        """Persist fake-storage object bytes and metadata."""
        safe_key = ensure_safe_storage_key(key)
        metadata = StorageObjectMetadata(
            content_type=(content_type or "").split(";", 1)[0].strip().lower(),
            size_bytes=len(data),
            duration_seconds=(
                int(duration_seconds) if duration_seconds is not None else 600
            ),
        )
        if self._root_dir is None:
            self._objects[safe_key] = metadata
            return metadata
        object_path = self.object_path(safe_key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(data)
        self._objects[safe_key] = metadata
        self._write_disk_metadata(safe_key, metadata)
        return metadata

    def object_path(self, key: str) -> Path:
        """Return local fake-storage object path."""
        if self._root_dir is None:
            raise StorageMediaError("Fake storage root directory is not configured")
        safe_key = ensure_safe_storage_key(key)
        return self._root_dir / safe_key

    def _metadata_path(self, safe_key: str) -> Path:
        if self._root_dir is None:
            raise StorageMediaError("Fake storage root directory is not configured")
        return self._root_dir / f"{safe_key}.metadata.json"

    def _write_disk_metadata(
        self, safe_key: str, metadata: StorageObjectMetadata
    ) -> None:
        if self._root_dir is None:
            return
        metadata_path = self._metadata_path(safe_key)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "content_type": metadata.content_type,
                    "size_bytes": int(metadata.size_bytes),
                    "duration_seconds": metadata.duration_seconds,
                }
            ),
            encoding="utf-8",
        )

    def _read_disk_metadata(self, safe_key: str) -> StorageObjectMetadata | None:
        if self._root_dir is None:
            return None
        metadata_path = self._metadata_path(safe_key)
        if not metadata_path.exists():
            object_path = self.object_path(safe_key)
            if not object_path.exists():
                return None
            return StorageObjectMetadata(
                content_type="application/octet-stream",
                size_bytes=int(object_path.stat().st_size),
            )
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return StorageObjectMetadata(
            content_type=str(payload.get("content_type") or "application/octet-stream"),
            size_bytes=int(payload.get("size_bytes") or 0),
            duration_seconds=(
                int(payload["duration_seconds"])
                if payload.get("duration_seconds") is not None
                else None
            ),
        )

    def _delete_disk_object(self, safe_key: str) -> None:
        if self._root_dir is None:
            return
        object_path = self.object_path(safe_key)
        metadata_path = self._metadata_path(safe_key)
        if object_path.exists():
            object_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

    def _validate_expiry(self, expires_at: int) -> None:
        if int(expires_at) < int(time.time()):
            raise StorageMediaError("Signed URL expired")

    def _token(self, *parts: str) -> str:
        raw = "|".join((*parts, self._signing_secret))
        return sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["FakeStorageMediaProvider"]
