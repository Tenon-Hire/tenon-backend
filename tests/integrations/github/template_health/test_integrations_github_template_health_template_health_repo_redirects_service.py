from __future__ import annotations

import base64

import httpx
import pytest

from app.integrations.github import GithubClient
from app.integrations.github.template_health import check_template_health
from app.integrations.github.template_health import (
    integrations_github_template_health_github_template_health_runner_service as runner_service,
)
from app.tasks.services.tasks_services_tasks_template_catalog_constants import (
    TEMPLATE_CATALOG,
)


@pytest.mark.asyncio
async def test_template_health_follows_redirects_for_all_catalog_entries():
    canonical_repo_full_name = "winoe-ai-repos/winoe-ws-42-coding"
    canonical_repo_path = f"/repos/{canonical_repo_full_name}"
    workflow_path = f"{canonical_repo_path}/contents/.github/workflows/winoe-ci.yml"
    workflow_content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/winoe-test-results.json",
        ]
    )
    redirect_paths = {}
    for meta in TEMPLATE_CATALOG.values():
        repo_full_name = meta["repo_full_name"]
        redirect_paths[f"/repos/{repo_full_name}"] = canonical_repo_path
        redirect_paths[
            f"/repos/{repo_full_name}/branches/main"
        ] = f"{canonical_repo_path}/branches/main"
        redirect_paths[
            f"/repos/{repo_full_name}/contents/.github/workflows/winoe-ci.yml"
        ] = workflow_path

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path in redirect_paths:
            return httpx.Response(
                301,
                headers={
                    "Location": f"https://api.github.com{redirect_paths[request.url.path]}"
                },
            )
        if request.method == "GET" and request.url.path == canonical_repo_path:
            return httpx.Response(
                200,
                json={
                    "full_name": canonical_repo_full_name,
                    "default_branch": "main",
                },
            )
        if (
            request.method == "GET"
            and request.url.path == f"{canonical_repo_path}/branches/main"
        ):
            return httpx.Response(200, json={"name": "main"})
        if request.method == "GET" and request.url.path == workflow_path:
            return httpx.Response(
                200,
                json={
                    "content": base64.b64encode(
                        workflow_content.encode("utf-8")
                    ).decode("ascii"),
                    "encoding": "base64",
                },
            )
        return httpx.Response(404, json={"message": "unexpected request"})

    client = GithubClient(
        base_url="https://api.github.com",
        token="token",
        transport=httpx.MockTransport(handler),
    )

    response = await check_template_health(
        client,
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=list(TEMPLATE_CATALOG.keys()),
    )

    assert response.ok is True
    assert [item.templateKey for item in response.templates] == list(
        TEMPLATE_CATALOG.keys()
    )
    assert all(item.ok for item in response.templates)
    assert all(
        item.repoFullName == TEMPLATE_CATALOG[item.templateKey]["repo_full_name"]
        for item in response.templates
    )


@pytest.mark.asyncio
async def test_template_health_reports_unreachable_catalog_entries_explicitly(
    monkeypatch,
):
    stale_repo_full_name = "winoe-templates/stale-template"
    monkeypatch.setattr(
        runner_service,
        "TEMPLATE_CATALOG",
        {"stale-template": {"repo_full_name": stale_repo_full_name}},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.method == "GET"
            and request.url.path == f"/repos/{stale_repo_full_name}"
        ):
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(404, json={"message": "unexpected request"})

    client = GithubClient(
        base_url="https://api.github.com",
        token="token",
        transport=httpx.MockTransport(handler),
    )

    response = await check_template_health(
        client,
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=["stale-template"],
    )

    assert response.ok is False
    assert response.templates[0].ok is False
    assert response.templates[0].errors == ["repo_not_found"]
    assert response.templates[0].checks.repoReachable is False
