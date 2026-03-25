from __future__ import annotations

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_s3_provider_includes_session_token_when_configured():
    provider = S3StorageMediaProvider(
        endpoint="https://storage.example.com/base",
        region="us-east-1",
        bucket="media-bucket",
        access_key_id="AKIA_TEST",
        secret_access_key="secret_test_key",
        session_token="session-token-value",
    )
    download_url = provider.create_signed_download_url(
        "candidate-sessions/1/tasks/1/recordings/object.mp4",
        120,
    )
    assert "X-Amz-Security-Token=session-token-value" in download_url
