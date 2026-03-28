from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_dispatch_and_wait_returns_normalized_result(monkeypatch):
    client = _StubClient()
    runner = GithubActionsRunner(
        client,
        workflow_file="ci.yml",
        poll_interval_seconds=0.01,
        max_poll_seconds=0.1,
    )

    async def fake_parse(repo, run_id):
        return (
            ParsedTestResults(
                passed=2, failed=1, total=3, stdout="ok", stderr="", summary={"s": 1}
            ),
            None,
        )

    monkeypatch.setattr(runner, "_parse_artifacts", fake_parse)

    result = await runner.dispatch_and_wait(
        repo_full_name="org/repo", ref="main", inputs={"a": "b"}
    )

    assert client.dispatched is True
    assert result.status == "passed"
    assert result.passed == 2
    assert result.failed == 1
    assert result.total == 3
    assert result.stdout == "ok"
    assert result.raw and result.raw["summary"]["s"] == 1
