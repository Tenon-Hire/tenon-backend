from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_template_health_repo_forbidden_classified():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            raise GithubError("denied", status_code=403)

    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=[next(iter(TEMPLATE_CATALOG))],
    )
    assert "github_forbidden" in response.templates[0].errors
