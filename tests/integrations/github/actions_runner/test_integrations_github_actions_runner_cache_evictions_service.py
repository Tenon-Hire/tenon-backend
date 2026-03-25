from __future__ import annotations

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


def test_cache_evictions():
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )
    runner._max_cache_entries = 1
    runner._cache_run_result(
        ("org/repo", 1),
        ActionsRunResult(
            status="running",
            run_id=1,
            conclusion=None,
            passed=None,
            failed=None,
            total=None,
            stdout=None,
            stderr=None,
            head_sha=None,
            html_url=None,
        ),
    )
    runner._cache_run_result(
        ("org/repo", 2),
        ActionsRunResult(
            status="running",
            run_id=2,
            conclusion=None,
            passed=None,
            failed=None,
            total=None,
            stdout=None,
            stderr=None,
            head_sha=None,
            html_url=None,
        ),
    )
    assert ("org/repo", 1) not in runner._run_cache
    runner._cache_artifact_result(("org/repo", 1, 1), None, None)
    runner._cache_artifact_result(("org/repo", 1, 2), None, None)
    assert ("org/repo", 1, 1) not in runner._artifact_cache
    runner._cache_artifact_result(("org/repo", 3, 3), None, None)
    runner._cache_artifact_list(("org/repo", 3), [])
    runner._cache_artifact_list(("org/repo", 4), [])
    assert ("org/repo", 3, 3) not in runner._artifact_cache
