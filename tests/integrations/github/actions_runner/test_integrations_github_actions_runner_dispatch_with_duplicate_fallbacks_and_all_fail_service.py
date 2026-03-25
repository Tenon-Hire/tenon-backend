from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_with_duplicate_fallbacks_and_all_fail(monkeypatch):
    class StubClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.calls = []

        async def trigger_workflow_dispatch(self, repo_full_name, wf, ref, inputs=None):
            self.calls.append(wf)
            raise GithubError("missing", status_code=404)

    client = StubClient()
    runner = GithubActionsRunner(client, workflow_file="preferred.yml")
    runner._workflow_fallbacks = ["preferred.yml", "preferred.yml"]

    with pytest.raises(GithubError):
        await runner._dispatch_with_fallbacks("org/repo", ref="main", inputs=None)

    assert client.calls == ["preferred.yml"]
