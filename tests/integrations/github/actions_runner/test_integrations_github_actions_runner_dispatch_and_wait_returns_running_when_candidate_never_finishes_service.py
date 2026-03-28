from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_and_wait_returns_running_when_candidate_never_finishes(
    monkeypatch,
):
    class SlowClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.calls = 0

        async def trigger_workflow_dispatch(self, *args, **kwargs):
            return None

        async def list_workflow_runs(self, *_a, **_k):
            self.calls += 1
            now = datetime.now(UTC).isoformat()
            return [
                WorkflowRun(
                    id=8,
                    status="queued",
                    conclusion=None,
                    html_url="https://example.com/run/8",
                    head_sha="sha8",
                    artifact_count=0,
                    event="workflow_dispatch",
                    created_at=now,
                )
            ]

    runner = GithubActionsRunner(
        SlowClient(),
        workflow_file="ci.yml",
        poll_interval_seconds=0.01,
        max_poll_seconds=0.02,
    )
    result = await runner.dispatch_and_wait(repo_full_name="org/repo", ref="main")
    assert result.status == "running"
