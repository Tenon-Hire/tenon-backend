from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_s3_provider_init_validates_required_configuration():
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="",
            region="us-east-1",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="us-east-1",
            bucket="",
            access_key_id="ak",
            secret_access_key="secret",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="https://s3.example",
            region="us-east-1",
            bucket="bucket",
            access_key_id="",
            secret_access_key="",
        )
    with pytest.raises(StorageMediaError):
        S3StorageMediaProvider(
            endpoint="not-a-url",
            region="us-east-1",
            bucket="bucket",
            access_key_id="ak",
            secret_access_key="secret",
        )
