from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_template_health_repo_not_found():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            raise GithubError("missing", status_code=404)

    template_key = next(iter(TEMPLATE_CATALOG))
    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=[template_key],
    )
    item = response.templates[0]
    assert item.ok is False
    assert "repo_not_found" in item.errors
