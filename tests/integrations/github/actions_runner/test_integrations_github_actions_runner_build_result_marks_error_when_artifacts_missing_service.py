from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_build_result_marks_error_when_artifacts_missing():
    class MissingArtifactClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")

        async def list_artifacts(self, *_a, **_k):
            return []

    runner = GithubActionsRunner(MissingArtifactClient(), workflow_file="ci.yml")
    run = WorkflowRun(
        id=101,
        status="completed",
        conclusion="success",
        html_url="https://example.com/run/101",
        head_sha="sha101",
        artifact_count=0,
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat(),
    )
    result = await runner._build_result("org/repo", run)
    assert result.status == "error"
    assert result.raw and result.raw.get("artifact_error") == "artifact_missing"
    assert result.stderr and "artifact" in result.stderr.lower()
