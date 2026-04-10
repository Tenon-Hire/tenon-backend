from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_template_health_default_branch_unusable():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            raise GithubError("bad branch")

        async def get_file_contents(
            self, repo_full_name: str, file_path: str, *, ref: str | None = None
        ):
            return {"content": "ZmlsZQ==", "encoding": "base64"}

    template_key = next(iter(TEMPLATE_CATALOG))
    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=[template_key],
    )
    item = response.templates[0]
    assert item.ok is False
    assert "default_branch_unusable" in item.errors
