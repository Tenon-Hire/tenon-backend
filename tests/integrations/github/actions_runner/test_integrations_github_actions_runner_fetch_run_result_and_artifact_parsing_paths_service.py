from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_fetch_run_result_and_artifact_parsing_paths(monkeypatch):
    class ArtifactClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")

        async def get_workflow_run(self, *_a, **_k):
            now = datetime.now(UTC).isoformat()
            return WorkflowRun(
                id=12,
                status="completed",
                conclusion="failure",
                html_url="https://example.com/run/12",
                head_sha="sha12",
                artifact_count=1,
                event="workflow_dispatch",
                created_at=now,
            )

        async def list_artifacts(self, *_a, **_k):
            return [
                {"id": 0, "expired": True},
                {"id": None},
                {"id": 99, "name": "other"},
            ]

        async def download_artifact_zip(self, *_a, **_k):
            raise GithubError("fail")

    runner = GithubActionsRunner(ArtifactClient(), workflow_file="ci.yml")
    result = await runner.fetch_run_result(repo_full_name="org/repo", run_id=12)
    assert result.conclusion == "failure"
    assert result.raw["artifact_count"] == 1
