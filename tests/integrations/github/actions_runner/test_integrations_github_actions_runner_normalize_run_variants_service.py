from __future__ import annotations

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


def test_normalize_run_variants():
    client = _StubClient()
    runner = GithubActionsRunner(client, workflow_file="ci.yml")
    success = runner._normalize_run(
        WorkflowRun(
            id=1,
            status="completed",
            conclusion="success",
            html_url=None,
            head_sha="sha",
        )
    )
    assert success.status == "passed"

    failure = runner._normalize_run(
        WorkflowRun(
            id=2,
            status="completed",
            conclusion="timed_out",
            html_url=None,
            head_sha="sha",
        )
    )
    assert failure.status == "failed"
    assert failure.conclusion == "timed_out"

    running = runner._normalize_run(
        WorkflowRun(
            id=3,
            status="in_progress",
            conclusion=None,
            html_url=None,
            head_sha=None,
        ),
        running=True,
    )
    assert running.status == "running"
