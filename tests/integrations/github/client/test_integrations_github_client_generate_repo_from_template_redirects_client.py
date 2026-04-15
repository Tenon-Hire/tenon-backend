from __future__ import annotations

import pytest

from tests.integrations.github.client.test_integrations_github_client_utils import *


@pytest.mark.asyncio
async def test_generate_repo_from_template_follows_redirects_and_normalizes_identity():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if (
            request.method == "POST"
            and request.url.path == "/repos/org/template/generate"
        ):
            return httpx.Response(
                302,
                headers={
                    "Location": "https://api.github.com/repos/winoe-ai-repos/winoe-ws-42-coding"
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/repos/winoe-ai-repos/winoe-ws-42-coding"
        ):
            return httpx.Response(
                200,
                json={
                    "owner": {"login": "winoe-ai-repos"},
                    "name": "winoe-ws-42-coding",
                    "full_name": "winoe-ai-repos/winoe-ws-42-coding",
                    "default_branch": "main",
                    "id": 123,
                },
            )
        return httpx.Response(404, json={"message": "unexpected request"})

    client = _mock_client(handler)
    repo = await client.generate_repo_from_template(
        template_full_name="org/template",
        new_repo_name="winoe-ws-42-coding",
        owner="winoe-ai-repos",
    )

    assert repo["owner"] == {"login": "winoe-ai-repos"}
    assert repo["name"] == "winoe-ws-42-coding"
    assert repo["full_name"] == "winoe-ai-repos/winoe-ws-42-coding"
    assert repo["canonical_owner"] == "winoe-ai-repos"
    assert repo["canonical_name"] == "winoe-ws-42-coding"
    assert repo["canonical_full_name"] == "winoe-ai-repos/winoe-ws-42-coding"
    assert calls == [
        ("POST", "/repos/org/template/generate"),
        ("GET", "/repos/winoe-ai-repos/winoe-ws-42-coding"),
    ]


@pytest.mark.asyncio
async def test_generate_repo_from_template_rejects_owner_mismatch():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "owner": {"login": "wrong-org"},
                "name": "winoe-ws-42-coding",
                "full_name": "wrong-org/winoe-ws-42-coding",
                "default_branch": "main",
            },
        )

    client = _mock_client(handler)

    with pytest.raises(GithubError):
        await client.generate_repo_from_template(
            template_full_name="org/template",
            new_repo_name="winoe-ws-42-coding",
            owner="winoe-ai-repos",
        )


@pytest.mark.asyncio
async def test_generate_repo_from_template_rejects_repo_name_mismatch():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "owner": {"login": "winoe-ai-repos"},
                "name": "wrong-repo",
                "full_name": "winoe-ai-repos/wrong-repo",
                "default_branch": "main",
            },
        )

    client = _mock_client(handler)

    with pytest.raises(GithubError):
        await client.generate_repo_from_template(
            template_full_name="org/template",
            new_repo_name="winoe-ws-42-coding",
            owner="winoe-ai-repos",
        )


@pytest.mark.asyncio
async def test_generate_repo_from_template_requires_destination_org():
    client = _mock_client(lambda _request: pytest.fail("request should not be sent"))

    with pytest.raises(GithubError, match="Destination GitHub org is not configured"):
        await client.generate_repo_from_template(
            template_full_name="org/template",
            new_repo_name="winoe-ws-42-coding",
        )
