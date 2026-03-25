from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_s3_provider_signing_and_validation_edges():
    provider = _build_s3_provider()
    upload_url = provider.create_signed_upload_url(
        "candidate-sessions/1/tasks/4/recordings/demo.mp4",
        "video/mp4",
        100,
        900,
    )
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in upload_url
    assert "X-Amz-SignedHeaders=content-type%3Bhost" in upload_url
    assert (
        "/base/media-bucket/candidate-sessions/1/tasks/4/recordings/demo.mp4"
        in upload_url
    )

    download_url = provider.create_signed_download_url(
        "candidate-sessions/1/tasks/4/recordings/demo.mp4",
        900,
    )
    assert "X-Amz-SignedHeaders=host" in download_url

    with pytest.raises(StorageMediaError):
        provider.create_signed_download_url(
            "candidate-sessions/1/tasks/4/recordings/demo.mp4",
            0,
        )
    with pytest.raises(StorageMediaError):
        provider.create_signed_upload_url(
            "candidate-sessions/1/tasks/4/recordings/demo.mp4",
            "",
            10,
            900,
        )
