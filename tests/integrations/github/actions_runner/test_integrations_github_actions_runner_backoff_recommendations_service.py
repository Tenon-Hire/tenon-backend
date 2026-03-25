from __future__ import annotations

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


def test_backoff_recommendations():
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"),
        workflow_file="wf",
        poll_interval_seconds=1.0,
    )
    key = ("org/repo", 55)
    running = ActionsRunResult(
        status="running",
        run_id=55,
        conclusion=None,
        passed=None,
        failed=None,
        total=None,
        stdout=None,
        stderr=None,
        head_sha=None,
        html_url=None,
    )
    runner._apply_backoff(key, running)
    assert running.poll_after_ms == 1000

    running_again = ActionsRunResult(
        status="running",
        run_id=55,
        conclusion=None,
        passed=None,
        failed=None,
        total=None,
        stdout=None,
        stderr=None,
        head_sha=None,
        html_url=None,
    )
    runner._apply_backoff(key, running_again)
    assert running_again.poll_after_ms == 2000

    finished = ActionsRunResult(
        status="passed",
        run_id=55,
        conclusion="success",
        passed=1,
        failed=0,
        total=1,
        stdout=None,
        stderr=None,
        head_sha=None,
        html_url=None,
    )
    runner._apply_backoff(key, finished)
    assert finished.poll_after_ms is None
    assert key not in runner._poll_attempts
    errored = ActionsRunResult(
        status="error",
        run_id=56,
        conclusion=None,
        passed=None,
        failed=None,
        total=None,
        stdout=None,
        stderr=None,
        head_sha=None,
        html_url=None,
    )
    runner._apply_backoff(("org/repo", 56), errored)
    assert errored.poll_after_ms is None
