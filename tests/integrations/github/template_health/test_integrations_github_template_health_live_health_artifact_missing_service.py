from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_live_health_artifact_missing():
    class StubGithubClient:
        async def get_repo(self, repo_full_name: str):
            return {"default_branch": "main"}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "abc"}}

        async def get_file_contents(
            self, repo_full_name: str, file_path: str, *, ref: str | None = None
        ):
            return _workflow_file_contents()

        async def trigger_workflow_dispatch(self, *args, **kwargs):
            return None

        async def list_workflow_runs(self, *args, **kwargs):
            return [_completed_run()]

        async def list_artifacts(self, *args, **kwargs):
            return []

    template_key = next(iter(TEMPLATE_CATALOG))
    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="live",
        template_keys=[template_key],
        timeout_seconds=5,
    )
    item = response.templates[0]
    assert "artifact_missing" in item.errors
