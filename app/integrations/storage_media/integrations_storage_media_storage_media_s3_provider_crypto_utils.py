"""Application module for integrations storage media storage media s3 provider crypto utils workflows."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
    ensure_safe_storage_key,
)


def _bucket_host(bucket: str, host: str) -> str:
    if ":" in host:
        bare_host, port = host.rsplit(":", 1)
        return f"{bucket}.{bare_host}:{port}"
    return f"{bucket}.{host}"


def _canonical_query_string(params: dict[str, str]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        pairs.append(
            (
                quote(str(key), safe="-_.~"),
                quote(str(value), safe="-_.~"),
            )
        )
    pairs.sort(key=lambda item: (item[0], item[1]))
    return "&".join(f"{key}={value}" for key, value in pairs)


def _sign(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def _derive_signing_key(
    *, secret_access_key: str, date_stamp: str, region: str, service: str
) -> bytes:
    k_date = _sign(f"AWS4{secret_access_key}".encode(), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    return _sign(k_service, "aws4_request")


def _object_url_parts(provider, key: str) -> tuple[str, str, str]:
    base_path = (provider._parsed_endpoint.path or "").strip("/")
    host = provider._parsed_endpoint.netloc
    if provider._use_path_style:
        raw_path_parts = [part for part in (base_path, provider._bucket, key) if part]
    else:
        host = _bucket_host(provider._bucket, host)
        raw_path_parts = [part for part in (base_path, key) if part]
    raw_path = "/" + "/".join(raw_path_parts)
    canonical_uri = quote(raw_path, safe="/-_.~")
    base_url = f"{provider._parsed_endpoint.scheme}://{host}"
    return host, canonical_uri, base_url


def _presign(
    provider,
    *,
    method: str,
    key: str,
    expires_seconds: int,
    extra_headers: dict[str, str],
    algorithm: str,
    payload_hash: str,
    service: str,
    max_expires_seconds: int,
) -> str:
    safe_key = ensure_safe_storage_key(key)
    ttl = int(expires_seconds)
    if ttl <= 0 or ttl > max_expires_seconds:
        raise StorageMediaError("expires_seconds must be between 1 and 604800")
    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    credential_scope = f"{date_stamp}/{provider._region}/{service}/aws4_request"
    host, canonical_uri, base_url = _object_url_parts(provider, safe_key)
    headers: dict[str, str] = {"host": host}
    for header_name, header_value in extra_headers.items():
        headers[header_name.strip().lower()] = " ".join(header_value.strip().split())
    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))
    query = {
        "X-Amz-Algorithm": algorithm,
        "X-Amz-Credential": f"{provider._access_key_id}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(ttl),
        "X-Amz-SignedHeaders": signed_headers,
    }
    if provider._session_token:
        query["X-Amz-Security-Token"] = provider._session_token
    canonical_query = _canonical_query_string(query)
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    canonical_request_hash = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = "\n".join(
        [algorithm, amz_date, credential_scope, canonical_request_hash]
    )
    signing_key = _derive_signing_key(
        secret_access_key=provider._secret_access_key,
        date_stamp=date_stamp,
        region=provider._region,
        service=service,
    )
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{base_url}{canonical_uri}?{canonical_query}&X-Amz-Signature={signature}"


__all__ = ["_presign"]
