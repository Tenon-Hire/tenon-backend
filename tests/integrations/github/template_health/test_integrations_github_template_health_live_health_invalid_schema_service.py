from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_live_health_invalid_schema():
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
            return [{"id": 1, "name": "winoe-test-results", "expired": False}]

        async def download_artifact_zip(self, *args, **kwargs):
            body = (
                '{"passed": "3", "failed": 0, "total": 3, "stdout": "", "stderr": ""}'
            )
            return _make_zip({"winoe-test-results.json": body})

    template_key = next(iter(TEMPLATE_CATALOG))
    response = await check_template_health(
        StubGithubClient(),
        workflow_file="winoe-ci.yml",
        mode="live",
        template_keys=[template_key],
        timeout_seconds=5,
    )
    item = response.templates[0]
    assert "test_results_json_invalid_schema" in item.errors
