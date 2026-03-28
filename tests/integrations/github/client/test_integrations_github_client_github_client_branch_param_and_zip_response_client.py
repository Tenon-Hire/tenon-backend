from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_github_client_branch_param_and_zip_response():
    seen_branch = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "runs" in request.url.path and "workflows" in request.url.path:
            seen_branch["value"] = request.url.params.get("branch")
            return httpx.Response(200, json={"workflow_runs": []})
        if request.url.path.endswith("/zip"):
            return httpx.Response(
                200, headers={"Content-Type": "application/zip"}, content=b"zipdata"
            )
        return httpx.Response(200, json={})

    client = _mock_client(handler)
    await client.list_workflow_runs("org/repo", "wf.yml", branch="feature")
    assert seen_branch["value"] == "feature"

    data = await client._request("GET", "/zip")
    assert data == b"zipdata"
