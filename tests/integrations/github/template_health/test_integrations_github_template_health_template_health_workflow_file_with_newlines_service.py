from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_template_health_workflow_file_with_newlines():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "abc"}}

        async def get_file_contents(
            self, repo_full_name: str, file_path: str, *, ref: str | None = None
        ):
            content = "\n".join(
                [
                    "uses: actions/upload-artifact@v4",
                    "name: winoe-test-results",
                    "path: artifacts/winoe-test-results.json",
                ]
            )
            encoded = base64.encodebytes(content.encode("utf-8")).decode("ascii")
            return {"content": encoded, "encoding": "base64"}

    template_key = next(iter(TEMPLATE_CATALOG))
    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="static",
        template_keys=[template_key],
    )
    item = response.templates[0]
    assert item.checks.workflowFileExists is True
    assert "workflow_file_unreadable" not in item.errors
