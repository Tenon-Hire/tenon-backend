from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


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
        if path == "/user":
            return {"login": "RobelKDev"}
        if path.endswith("/user/codespaces/codespace-123"):
            return {"repository": {"full_name": "owner/name"}, "state": "Available"}
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
    await client.create_or_update_file(
        "owner/name",
        "README.md",
        content="hello",
        message="init",
        branch="main",
    )
    assert await client.get_authenticated_user_login() == "RobelKDev"
    await client.create_codespace("owner/name", ref="main")
    await client.get_codespace("owner/name", "codespace-123")
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
    assert any(
        path == "/user/codespaces/codespace-123" for path, _ in calls["get_json"]
    )
    assert any(path == "/user" for path, _ in calls["get_json"])
    assert any(path.endswith("/git/blobs") for path, _, _ in calls["post_json"])
    assert any(path.endswith("/git/trees") for path, _, _ in calls["post_json"])
    assert any(path.endswith("/git/commits") for path, _, _ in calls["post_json"])
    assert any(
        method == "PATCH" and path.endswith("/repos/owner/name")
        for method, path, *_rest in calls["request"]
    )
    assert any(
        method == "PUT"
        and path.endswith("/contents/README.md")
        and json["branch"] == "main"
        for method, path, _, json, _ in calls["request"]
    )
    assert any(
        method == "DELETE" and path.endswith("/repos/owner/name")
        for method, path, *_rest in calls["request"]
    )
    assert any(
        method == "PATCH" and path.endswith("/git/refs/heads/main")
        for method, path, *_rest in calls["request"]
    )
    assert any(path.endswith("/codespaces") for path, _, _ in calls["post_json"])

    with pytest.raises(GithubError):
        await client.get_repo("bad-name")
