"""Application module for integrations storage media storage media s3 provider network utils workflows."""

from __future__ import annotations

import time
from urllib.error import HTTPError


def get_object_metadata(
    provider,
    *,
    key: str,
    request_cls,
    urlopen_fn,
    storage_error_cls,
    metadata_cls,
    perf_record_external_wait,
    metadata_expires_seconds: int,
):
    """Return object metadata."""
    signed_head_url = provider._presign(
        method="HEAD",
        key=key,
        expires_seconds=metadata_expires_seconds,
        extra_headers={},
    )
    request = request_cls(signed_head_url, method="HEAD")
    started = time.perf_counter()
    try:
        with urlopen_fn(request, timeout=5) as response:
            content_length_raw = response.headers.get("Content-Length")
            if content_length_raw is None:
                raise storage_error_cls(
                    "Storage object metadata missing Content-Length header"
                )
            try:
                size_bytes = int(content_length_raw)
            except ValueError as exc:
                raise storage_error_cls(
                    "Storage object metadata returned invalid Content-Length"
                ) from exc
            if size_bytes < 0:
                raise storage_error_cls(
                    "Storage object metadata returned negative Content-Length"
                )
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            if not content_type:
                raise storage_error_cls(
                    "Storage object metadata missing Content-Type header"
                )
            return metadata_cls(content_type=content_type, size_bytes=size_bytes)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise storage_error_cls(
            f"Failed to inspect storage object metadata (status={exc.code})"
        ) from exc
    except OSError as exc:
        raise storage_error_cls("Failed to inspect storage object metadata") from exc
    finally:
        perf_record_external_wait("storage", (time.perf_counter() - started) * 1000.0)


def delete_object(
    provider,
    *,
    key: str,
    request_cls,
    urlopen_fn,
    storage_error_cls,
    perf_record_external_wait,
    metadata_expires_seconds: int,
) -> None:
    """Delete object."""
    signed_delete_url = provider._presign(
        method="DELETE",
        key=key,
        expires_seconds=metadata_expires_seconds,
        extra_headers={},
    )
    request = request_cls(signed_delete_url, method="DELETE")
    started = time.perf_counter()
    try:
        with urlopen_fn(request, timeout=5):
            return
    except HTTPError as exc:
        if exc.code == 404:
            return
        raise storage_error_cls(
            f"Failed to delete storage object (status={exc.code})"
        ) from exc
    except OSError as exc:
        raise storage_error_cls("Failed to delete storage object") from exc
    finally:
        perf_record_external_wait("storage", (time.perf_counter() - started) * 1000.0)


__all__ = ["delete_object", "get_object_metadata"]
