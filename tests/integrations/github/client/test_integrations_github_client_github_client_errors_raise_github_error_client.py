from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_github_client_errors_raise_github_error():
    """4xx/5xx responses should bubble up as GithubError with status codes."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "missing"})

    client = _mock_client(handler)

    with pytest.raises(GithubError) as excinfo:
        await client.list_workflow_runs("org/repo", "ci.yml")
    assert excinfo.value.status_code == 404

    with pytest.raises(GithubError):
        client._split_full_name("bad-name")
