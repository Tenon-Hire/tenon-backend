from __future__ import annotations

import httpx
import pytest

from app.integrations.github.client import GithubClient, GithubError


def _mock_client(handler) -> GithubClient:
    return GithubClient(
        base_url="https://api.github.com",
        token="token123",
        transport=httpx.MockTransport(handler),
    )


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


def test_split_full_name_rejects_empty_owner_or_repo():
    client = _mock_client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(GithubError):
        client._split_full_name("owner/")


@pytest.mark.asyncio
async def test_github_client_get_bytes_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _mock_client(handler)
    with pytest.raises(GithubError):
        await client.download_artifact_zip("org/repo", 9)


@pytest.mark.asyncio
async def test_github_client_misc_methods(monkeypatch):
    client = GithubClient(base_url="https://api.github.com", token="t")
    calls: dict[str, list[tuple]] = {"get_json": [], "post_json": [], "request": []}

    async def _fake_get_json(path: str, params=None):
        calls["get_json"].append((path, params))
        if path.endswith("/commits") and isinstance(params, dict):
            if "sha" in params:
                return [{"sha": "abc", "commit": {"message": "m"}}]
            return {"not": "a-list"}
        return {}

    async def _fake_post_json(path: str, *, json: dict, expect_body: bool = True):
        calls["post_json"].append((path, json, expect_body))
        return {"sha": "created-sha"}

    async def _fake_request(
        method: str,
        path: str,
        *,
        params=None,
        json=None,
        expect_body: bool = True,
    ):
        calls["request"].append((method, path, params, json, expect_body))
        return {"ok": True}

    async def _fake_get_bytes(*_a, **_k):
        return b"zipdata"

    monkeypatch.setattr(client, "_get_json", _fake_get_json)
    monkeypatch.setattr(client, "_post_json", _fake_post_json)
    monkeypatch.setattr(client, "_request", _fake_request)
    monkeypatch.setattr(client, "_get_bytes", _fake_get_bytes)
    await client.get_repo("owner/name")
    await client.get_file_contents("owner/name", "path.txt", ref="main")
    await client.get_compare("owner/name", "a", "b")
    await client.list_artifacts("owner/name", 1)
    await client.download_artifact_zip("owner/name", 1)
    await client.get_ref("owner/name", "heads/main")
    await client.get_commit("owner/name", "abc123")
    await client.create_blob("owner/name", content="hello")
    await client.create_tree(
        "owner/name",
        tree=[{"path": "README.md", "mode": "100644", "type": "blob", "sha": "abc"}],
        base_tree="base-tree",
    )
    await client.create_tree(
        "owner/name",
        tree=[{"path": "README.md", "mode": "100644", "type": "blob", "sha": "abc"}],
    )
    await client.create_commit(
        "owner/name",
        message="msg",
        tree="tree-sha",
        parents=["parent-sha"],
    )
    await client.archive_repo("owner/name")
    await client.delete_repo("owner/name")
    await client.update_ref(
        "owner/name",
        ref="heads/main",
        sha="next-sha",
        force=False,
    )
    commits = await client.list_commits("owner/name", sha="main", per_page=10)
    assert commits and commits[0]["sha"] == "abc"
    assert await client.list_commits("owner/name", per_page=10) == []

    class DummyClient:
        async def aclose(self):
            pass

    client._client = DummyClient()
    await client.aclose()

    assert any(path.endswith("/git/ref/heads/main") for path, _ in calls["get_json"])
    assert any(path.endswith("/git/commits/abc123") for path, _ in calls["get_json"])
    assert any(path.endswith("/git/blobs") for path, _, _ in calls["post_json"])
    assert any(path.endswith("/git/trees") for path, _, _ in calls["post_json"])
    assert any(path.endswith("/git/commits") for path, _, _ in calls["post_json"])
    assert any(
        method == "PATCH" and path.endswith("/repos/owner/name")
        for method, path, *_rest in calls["request"]
    )
    assert any(
        method == "DELETE" and path.endswith("/repos/owner/name")
        for method, path, *_rest in calls["request"]
    )
    assert any(
        method == "PATCH" and path.endswith("/git/refs/heads/main")
        for method, path, *_rest in calls["request"]
    )

    with pytest.raises(GithubError):
        await client.get_repo("bad-name")
