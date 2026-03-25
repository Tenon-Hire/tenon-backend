from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_github_client_get_bytes_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _mock_client(handler)
    with pytest.raises(GithubError):
        await client.download_artifact_zip("org/repo", 9)
