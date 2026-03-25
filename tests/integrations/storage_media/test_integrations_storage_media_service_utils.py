from __future__ import annotations

# helper import baseline for restructure-compat
from urllib.error import HTTPError

from fastapi import HTTPException

import app.integrations.storage_media.integrations_storage_media_storage_media_s3_provider_client as s3_module
from app.config import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    S3StorageMediaProvider,
    StorageMediaError,
    ensure_safe_storage_key,
    get_storage_media_provider,
)
from app.media.services import (
    build_recording_storage_key,
    parse_recording_public_id,
    validate_upload_input,
)
from app.media.services.media_services_media_keys_service import (
    normalize_extension,
)


def _build_s3_provider(*, use_path_style: bool = True) -> S3StorageMediaProvider:
    return S3StorageMediaProvider(
        endpoint="https://storage.example.com:9000/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        use_path_style=use_path_style,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
