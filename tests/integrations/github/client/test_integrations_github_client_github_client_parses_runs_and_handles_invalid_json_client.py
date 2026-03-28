from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_github_client_parses_runs_and_handles_invalid_json():
    """Ensure list/get run parsing and JSON error handling."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/runs/5"):
            return httpx.Response(
                200,
                json={
                    "id": 5,
                    "status": "queued",
                    "conclusion": None,
                    "html_url": "https://example.com/run/5",
                    "head_sha": "sha5",
                    "artifacts_count": 0,
                    "event": "workflow_dispatch",
                    "created_at": "2024-01-01T00:00:00Z",
                },
            )
        if "/runs" in path and "workflows" in path:
            return httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "id": 6,
                            "status": "completed",
                            "conclusion": "success",
                            "html_url": "https://example.com/run/6",
                            "head_sha": "sha6",
                            "artifacts": 2,
                            "event": "workflow_dispatch",
                            "created_at": "2024-01-02T00:00:00Z",
                        }
                    ]
                },
            )
        if path.endswith("/bad-json"):
            return httpx.Response(200, text="not-json")
        return httpx.Response(200, json={})

    client = _mock_client(handler)
    run = await client.get_workflow_run("org/repo", 5)
    assert run.id == 5 and run.status == "queued"

    runs = await client.list_workflow_runs("org/repo", "wf.yml")
    assert runs[0].conclusion == "success"

    with pytest.raises(GithubError):
        await client._get_json("/bad-json")
