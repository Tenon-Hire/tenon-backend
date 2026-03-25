from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_with_no_fallbacks(monkeypatch):
    client = GithubClient(base_url="https://api.github.com", token="t")
    runner = GithubActionsRunner(client, workflow_file="ci.yml")
    runner._workflow_fallbacks = []
    with pytest.raises(GithubError):
        await runner._dispatch_with_fallbacks("org/repo", ref="main", inputs=None)
