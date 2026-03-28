from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_build_result_artifact_error_sets_error(monkeypatch):
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )

    async def fake_parse(repo, run_id):
        return None, "artifact_missing"

    monkeypatch.setattr(runner, "_parse_artifacts", fake_parse)
    run = WorkflowRun(
        id=1,
        status="completed",
        conclusion="success",
        html_url=None,
        head_sha=None,
        artifact_count=0,
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat(),
    )
    result = await runner._build_result("org/repo", run)
    assert result.status == "error"
    assert "artifact_error" in result.raw
