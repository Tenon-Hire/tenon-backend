from __future__ import annotations

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


def test_normalize_run_timed_out_and_queued():
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )
    queued = runner._normalize_run(
        WorkflowRun(
            id=5,
            status="queued",
            conclusion=None,
            html_url=None,
            head_sha="sha",
        )
    )
    assert queued.status == "running"

    timed_out = runner._normalize_run(
        WorkflowRun(
            id=6, status="completed", conclusion=None, html_url=None, head_sha="sha6"
        ),
        timed_out=True,
    )
    assert timed_out.status == "running"
    unknown = runner._normalize_run(
        WorkflowRun(
            id=9,
            status="strange",
            conclusion=None,
            html_url=None,
            head_sha="sha9",
        )
    )
    assert unknown.status == "error"
