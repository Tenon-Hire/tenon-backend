from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_build_result_artifact_error_sets_raw_when_missing(monkeypatch):
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )

    async def fake_parse(repo, run_id):
        return None, "artifact_missing"

    monkeypatch.setattr(runner, "_parse_artifacts", fake_parse)
    original_normalize = runner._normalize_run

    def normalize_with_empty_raw(run, *, timed_out=False, running=False):
        res = original_normalize(run, timed_out=timed_out, running=running)
        res.raw = None
        return res

    monkeypatch.setattr(runner, "_normalize_run", normalize_with_empty_raw)
    run = WorkflowRun(
        id=2,
        status="completed",
        conclusion="failure",
        html_url=None,
        head_sha=None,
    )
    result = await runner._build_result("org/repo", run)
    assert result.raw["artifact_error"] == "artifact_missing"
