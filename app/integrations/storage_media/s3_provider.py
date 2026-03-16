from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from app.integrations.storage_media.base import (
    StorageMediaError,
    StorageObjectMetadata,
    ensure_safe_storage_key,
)

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
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_seconds: int,
    ) -> str:
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
        return self._presign(
            method="GET",
            key=key,
            expires_seconds=expires_seconds,
            extra_headers={},
        )

    def get_object_metadata(self, key: str) -> StorageObjectMetadata | None:
        signed_head_url = self._presign(
            method="HEAD",
            key=key,
            expires_seconds=_METADATA_EXPIRES_SECONDS,
            extra_headers={},
        )
        request = Request(signed_head_url, method="HEAD")
        try:
            with urlopen(request, timeout=5) as response:
                content_length_raw = response.headers.get("Content-Length")
                if content_length_raw is None:
                    raise StorageMediaError(
                        "Storage object metadata missing Content-Length header"
                    )
                try:
                    size_bytes = int(content_length_raw)
                except ValueError as exc:
                    raise StorageMediaError(
                        "Storage object metadata returned invalid Content-Length"
                    ) from exc
                if size_bytes < 0:
                    raise StorageMediaError(
                        "Storage object metadata returned negative Content-Length"
                    )
                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if not content_type:
                    raise StorageMediaError(
                        "Storage object metadata missing Content-Type header"
                    )
                return StorageObjectMetadata(
                    content_type=content_type,
                    size_bytes=size_bytes,
                )
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise StorageMediaError(
                f"Failed to inspect storage object metadata (status={exc.code})"
            ) from exc
        except OSError as exc:
            raise StorageMediaError(
                "Failed to inspect storage object metadata"
            ) from exc

    def delete_object(self, key: str) -> None:
        signed_delete_url = self._presign(
            method="DELETE",
            key=key,
            expires_seconds=_METADATA_EXPIRES_SECONDS,
            extra_headers={},
        )
        request = Request(signed_delete_url, method="DELETE")
        try:
            with urlopen(request, timeout=5):
                return
        except HTTPError as exc:
            # S3 delete is idempotent; treat missing objects as already deleted.
            if exc.code == 404:
                return
            raise StorageMediaError(
                f"Failed to delete storage object (status={exc.code})"
            ) from exc
        except OSError as exc:
            raise StorageMediaError("Failed to delete storage object") from exc

    def _presign(
        self,
        *,
        method: str,
        key: str,
        expires_seconds: int,
        extra_headers: dict[str, str],
    ) -> str:
        safe_key = ensure_safe_storage_key(key)
        ttl = int(expires_seconds)
        if ttl <= 0 or ttl > _MAX_EXPIRES_SECONDS:
            raise StorageMediaError("expires_seconds must be between 1 and 604800")

        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{self._region}/{_SERVICE}/aws4_request"

        host, canonical_uri, base_url = self._object_url_parts(safe_key)

        headers: dict[str, str] = {"host": host}
        for header_name, header_value in extra_headers.items():
            headers[header_name.strip().lower()] = " ".join(
                header_value.strip().split()
            )

        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(
            f"{name}:{headers[name]}\n" for name in sorted(headers)
        )

        query = {
            "X-Amz-Algorithm": _ALGORITHM,
            "X-Amz-Credential": f"{self._access_key_id}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(ttl),
            "X-Amz-SignedHeaders": signed_headers,
        }
        if self._session_token:
            query["X-Amz-Security-Token"] = self._session_token

        canonical_query = _canonical_query_string(query)
        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                canonical_query,
                canonical_headers,
                signed_headers,
                _PAYLOAD_HASH,
            ]
        )
        canonical_request_hash = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = "\n".join(
            [_ALGORITHM, amz_date, credential_scope, canonical_request_hash]
        )

        signing_key = _derive_signing_key(
            secret_access_key=self._secret_access_key,
            date_stamp=date_stamp,
            region=self._region,
            service=_SERVICE,
        )
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        final_query = f"{canonical_query}&X-Amz-Signature={signature}"
        return f"{base_url}{canonical_uri}?{final_query}"

    def _object_url_parts(self, key: str) -> tuple[str, str, str]:
        base_path = (self._parsed_endpoint.path or "").strip("/")
        key_path = key

        host = self._parsed_endpoint.netloc
        if self._use_path_style:
            raw_path_parts = [
                part for part in (base_path, self._bucket, key_path) if part
            ]
        else:
            host = _bucket_host(self._bucket, host)
            raw_path_parts = [part for part in (base_path, key_path) if part]

        raw_path = "/" + "/".join(raw_path_parts)
        canonical_uri = quote(raw_path, safe="/-_.~")
        base_url = f"{self._parsed_endpoint.scheme}://{host}"
        return host, canonical_uri, base_url


def _bucket_host(bucket: str, host: str) -> str:
    if ":" in host:
        bare_host, port = host.rsplit(":", 1)
        return f"{bucket}.{bare_host}:{port}"
    return f"{bucket}.{host}"


def _canonical_query_string(params: dict[str, str]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        encoded_key = quote(str(key), safe="-_.~")
        encoded_value = quote(str(value), safe="-_.~")
        pairs.append((encoded_key, encoded_value))
    pairs.sort(key=lambda item: (item[0], item[1]))
    return "&".join(f"{key}={value}" for key, value in pairs)


def _sign(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def _derive_signing_key(
    *,
    secret_access_key: str,
    date_stamp: str,
    region: str,
    service: str,
) -> bytes:
    k_date = _sign(f"AWS4{secret_access_key}".encode(), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    return _sign(k_service, "aws4_request")


__all__ = ["S3StorageMediaProvider"]
