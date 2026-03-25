from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_with_fallbacks_and_errors(monkeypatch):
    class StubClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.calls = []

        async def trigger_workflow_dispatch(self, repo_full_name, wf, ref, inputs=None):
            self.calls.append(wf)
            if wf == "preferred.yml":
                raise GithubError("missing", status_code=404)
            if wf == "bad.yml":
                raise GithubError("boom", status_code=500)
            return None

    client = StubClient()
    runner = GithubActionsRunner(client, workflow_file="preferred.yml")
    runner._workflow_fallbacks = ["preferred.yml", "fallback.yml"]
    used = await runner._dispatch_with_fallbacks("org/repo", ref="main", inputs=None)
    assert used == "fallback.yml"

    runner._workflow_fallbacks = ["bad.yml"]
    with pytest.raises(GithubError):
        await runner._dispatch_with_fallbacks("org/repo", ref="main", inputs=None)
