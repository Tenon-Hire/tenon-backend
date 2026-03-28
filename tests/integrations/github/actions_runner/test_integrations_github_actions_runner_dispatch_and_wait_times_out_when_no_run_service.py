from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_and_wait_times_out_when_no_run(monkeypatch):
    class EmptyClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")

        async def trigger_workflow_dispatch(self, *args, **kwargs):
            return None

        async def list_workflow_runs(self, *args, **kwargs):
            return []

    runner = GithubActionsRunner(
        EmptyClient(),
        workflow_file="ci.yml",
        poll_interval_seconds=0.01,
        max_poll_seconds=0.05,
    )
    with pytest.raises(GithubError):
        await runner.dispatch_and_wait(repo_full_name="org/repo", ref="main")
