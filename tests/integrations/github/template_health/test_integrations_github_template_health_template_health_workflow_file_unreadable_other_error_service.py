from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_template_health_workflow_file_unreadable_other_error():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "abc"}}

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("boom", status_code=500)

    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=[next(iter(TEMPLATE_CATALOG))],
    )
    assert "workflow_file_unreadable" in response.templates[0].errors
