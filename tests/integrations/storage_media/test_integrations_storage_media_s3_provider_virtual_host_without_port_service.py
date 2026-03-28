from __future__ import annotations

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_s3_provider_virtual_host_without_port():
    provider = S3StorageMediaProvider(
        endpoint="https://storage.example.com/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        use_path_style=False,
    )
    download_url = provider.create_signed_download_url(
        "candidate-sessions/2/tasks/6/recordings/demo.webm",
        120,
    )
    assert download_url.startswith("https://media-bucket.storage.example.com/")
    assert "/base/candidate-sessions/2/tasks/6/recordings/demo.webm" in download_url
