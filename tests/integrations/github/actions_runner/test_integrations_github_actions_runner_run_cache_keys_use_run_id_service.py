from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_run_cache_keys_use_run_id(monkeypatch):
    class CountingClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")
            self.calls = 0

        async def get_workflow_run(self, repo_full_name, run_id):
            self.calls += 1
            return WorkflowRun(
                id=run_id,
                status="completed",
                conclusion="success",
                html_url=None,
                head_sha="sha",
                artifact_count=0,
                event="workflow_dispatch",
                created_at=datetime.now(UTC).isoformat(),
            )

        async def list_artifacts(self, *_a, **_k):
            return []

    client = CountingClient()
    runner = GithubActionsRunner(client, workflow_file="ci.yml")

    async def _no_artifacts(repo, run_id):
        return None, None

    monkeypatch.setattr(runner, "_parse_artifacts", _no_artifacts)

    first = await runner.fetch_run_result(repo_full_name="org/repo", run_id=1)
    repeat_first = await runner.fetch_run_result(repo_full_name="org/repo", run_id=1)
    second = await runner.fetch_run_result(repo_full_name="org/repo", run_id=2)
    repeat_second = await runner.fetch_run_result(repo_full_name="org/repo", run_id=2)

    assert first.status == "passed"
    assert repeat_first.status == "passed"
    assert second.status == "passed"
    assert repeat_second.status == "passed"
    assert client.calls == 2
    await client.aclose()
