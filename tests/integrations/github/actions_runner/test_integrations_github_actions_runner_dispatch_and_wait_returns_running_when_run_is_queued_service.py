from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_and_wait_returns_running_when_run_is_queued(monkeypatch):
    class QueuedClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.list_calls = 0
            self.dispatched = 0

        async def trigger_workflow_dispatch(self, *args, **kwargs):
            self.dispatched += 1
            return None

        async def list_workflow_runs(self, *_a, **_k):
            self.list_calls += 1
            now = datetime.now(UTC).isoformat()
            return [
                WorkflowRun(
                    id=101,
                    status="queued",
                    conclusion=None,
                    html_url="https://example.com/run/101",
                    head_sha="sha101",
                    artifact_count=0,
                    event="workflow_dispatch",
                    created_at=now,
                )
            ]

    runner = GithubActionsRunner(
        QueuedClient(),
        workflow_file="evidence-capture.yml",
        poll_interval_seconds=0.01,
        max_poll_seconds=0.05,
    )

    async def _unexpected_build_result(*_a, **_k):
        raise AssertionError("build_result should not run for queued dispatches")

    monkeypatch.setattr(
        "app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_dispatch_loop_service.build_result",
        _unexpected_build_result,
    )

    result = await runner.dispatch_and_wait(repo_full_name="org/repo", ref="main")

    assert result.status == "running"
    assert result.run_id == 101
    assert runner.client.dispatched == 1
    assert runner.client.list_calls == 2
