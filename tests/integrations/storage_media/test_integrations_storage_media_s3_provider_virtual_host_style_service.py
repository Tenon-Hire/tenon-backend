from __future__ import annotations

from urllib.parse import urlsplit

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_s3_provider_virtual_host_style():
    provider = _build_s3_provider(use_path_style=False)
    download_url = provider.create_signed_download_url(
        "candidate-sessions/2/tasks/6/recordings/demo.webm",
        120,
    )
    parsed = urlsplit(download_url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "media-bucket.storage.example.com:9000"
    assert parsed.path == "/base/candidate-sessions/2/tasks/6/recordings/demo.webm"
