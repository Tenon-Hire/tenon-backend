"""Application module for integrations storage media storage media s3 provider client workflows."""

from __future__ import annotations

from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
    StorageObjectMetadata,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_s3_provider_crypto_utils import (
    _presign,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_s3_provider_network_utils import (
    delete_object as _delete_object_impl,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_s3_provider_network_utils import (
    get_object_metadata as _get_object_metadata_impl,
)
from app.shared.utils import shared_utils_perf_utils as perf

_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_PAYLOAD_HASH = "UNSIGNED-PAYLOAD"
_MAX_EXPIRES_SECONDS = 60 * 60 * 24 * 7
_METADATA_EXPIRES_SECONDS = 60


class S3StorageMediaProvider:
    """S3-compatible signed URL provider using SigV4 query auth."""

    def __init__(
        self,
        *,
        endpoint: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: str | None = None,
        use_path_style: bool = True,
    ) -> None:
        self._endpoint = (endpoint or "").rstrip("/")
        self._region = (region or "").strip()
        self._bucket = (bucket or "").strip()
        self._access_key_id = (access_key_id or "").strip()
        self._secret_access_key = (secret_access_key or "").strip()
        self._session_token = (session_token or "").strip() or None
        self._use_path_style = bool(use_path_style)
        if not self._endpoint:
            raise StorageMediaError("MEDIA_S3_ENDPOINT is required")
        if not self._region:
            raise StorageMediaError("MEDIA_S3_REGION is required")
        if not self._bucket:
            raise StorageMediaError("MEDIA_S3_BUCKET is required")
        if not self._access_key_id or not self._secret_access_key:
            raise StorageMediaError("S3 credentials are required")
        parsed = urlsplit(self._endpoint)
        if not parsed.scheme or not parsed.netloc:
            raise StorageMediaError("MEDIA_S3_ENDPOINT must be an absolute URL")
        self._parsed_endpoint = parsed

    def create_signed_upload_url(
        self, key: str, content_type: str, size_bytes: int, expires_seconds: int
    ) -> str:
        """Create signed upload url."""
        del size_bytes
        normalized_type = (content_type or "").strip()
        if not normalized_type:
            raise StorageMediaError("content_type is required")
        return self._presign(
            method="PUT",
            key=key,
            expires_seconds=expires_seconds,
            extra_headers={"content-type": normalized_type},
        )

    def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
        """Create signed download url."""
        return self._presign(
            method="GET", key=key, expires_seconds=expires_seconds, extra_headers={}
        )

    def get_object_metadata(self, key: str) -> StorageObjectMetadata | None:
        """Return object metadata."""
        return _get_object_metadata_impl(
            self,
            key=key,
            request_cls=Request,
            urlopen_fn=urlopen,
            storage_error_cls=StorageMediaError,
            metadata_cls=StorageObjectMetadata,
            perf_record_external_wait=perf.record_external_wait,
            metadata_expires_seconds=_METADATA_EXPIRES_SECONDS,
        )

    def delete_object(self, key: str) -> None:
        """Delete object."""
        return _delete_object_impl(
            self,
            key=key,
            request_cls=Request,
            urlopen_fn=urlopen,
            storage_error_cls=StorageMediaError,
            perf_record_external_wait=perf.record_external_wait,
            metadata_expires_seconds=_METADATA_EXPIRES_SECONDS,
        )

    def _presign(
        self,
        *,
        method: str,
        key: str,
        expires_seconds: int,
        extra_headers: dict[str, str],
    ) -> str:
        return _presign(
            self,
            method=method,
            key=key,
            expires_seconds=expires_seconds,
            extra_headers=extra_headers,
            algorithm=_ALGORITHM,
            payload_hash=_PAYLOAD_HASH,
            service=_SERVICE,
            max_expires_seconds=_MAX_EXPIRES_SECONDS,
        )


__all__ = ["S3StorageMediaProvider"]
