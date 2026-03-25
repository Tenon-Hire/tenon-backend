from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_github_client_happy_paths():
    """Exercise the primary REST helpers with a mock transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/generate"):
            return httpx.Response(201, json={"full_name": "org/new-repo"})
        if request.method == "PUT" and "/collaborators/" in request.url.path:
            return httpx.Response(200, json={"ok": True})
        if request.method == "DELETE" and "/collaborators/" in request.url.path:
            return httpx.Response(204)
        if request.method == "PATCH" and request.url.path == "/repos/org/repo":
            return httpx.Response(200, json={"archived": True})
        if request.method == "DELETE" and request.url.path == "/repos/org/repo":
            return httpx.Response(204)
        if request.method == "POST" and "/dispatches" in request.url.path:
            return httpx.Response(204)
        if request.method == "GET" and "/branches/" in request.url.path:
            return httpx.Response(200, json={"name": "main"})
        if request.method == "GET" and "/compare/" in request.url.path:
            return httpx.Response(200, json={"ahead_by": 1})
        if request.method == "GET" and "/zip" in request.url.path:
            return httpx.Response(
                200,
                headers={"Content-Type": "application/zip"},
                content=b"zip-bytes",
            )
        if request.method == "GET" and "/artifacts" in request.url.path:
            return httpx.Response(200, json={"artifacts": [{"id": 1, "name": "a"}]})
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(handler)

    repo = await client.generate_repo_from_template(
        template_full_name="org/template",
        new_repo_name="new-repo",
        owner="org",
    )
    assert repo["full_name"] == "org/new-repo"

    collab = await client.add_collaborator("org/repo", "octocat")
    assert collab["ok"] is True
    removed = await client.remove_collaborator("org/repo", "octocat")
    assert removed == {}
    archived = await client.archive_repo("org/repo")
    assert archived["archived"] is True
    deleted = await client.delete_repo("org/repo")
    assert deleted == {}

    # No exception raised on 204/expect_body False
    await client.trigger_workflow_dispatch(
        "org/repo", "wf.yml", ref="main", inputs={"a": "b"}
    )

    branch = await client.get_branch("org/repo", "main")
    assert branch["name"] == "main"

    compare = await client.get_compare("org/repo", "base", "head")
    assert compare["ahead_by"] == 1

    artifacts = await client.list_artifacts("org/repo", 123)
    assert artifacts[0]["id"] == 1

    data = await client.download_artifact_zip("org/repo", 1)
    assert data == b"zip-bytes"
