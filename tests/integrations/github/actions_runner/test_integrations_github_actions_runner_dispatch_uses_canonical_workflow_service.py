from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_uses_canonical_evidence_capture_workflow_first():
    class StubClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.calls = []

        async def trigger_workflow_dispatch(self, repo_full_name, wf, ref, inputs=None):
            self.calls.append((repo_full_name, wf, ref, inputs))
            return None

    client = StubClient()
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")

    used = await runner._dispatch_with_fallbacks(
        "org/repo",
        ref="main",
        inputs={"trialId": "123"},
    )

    assert used == "winoe-evidence-capture.yml"
    assert client.calls == [
        ("org/repo", "winoe-evidence-capture.yml", "main", {"trialId": "123"})
    ]
