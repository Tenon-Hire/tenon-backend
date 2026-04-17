from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_run_code_submission_returns_without_diff_when_head_sha_missing(
    monkeypatch,
):
    workspace = SimpleNamespace(repo_full_name="owner/repo")
    result = ActionsRunResult(
        status="passed",
        run_id=1,
        conclusion="success",
        passed=1,
        failed=0,
        total=1,
        stdout="",
        stderr="",
        head_sha=None,
        html_url=None,
    )

    async def _fetch_workspace(*_a, **_k):
        return workspace, "main"

    async def _run_actions_tests(*_a, **_k):
        return result

    async def _record(*_a, **_k):
        return None

    monkeypatch.setattr(
        submit_task_runner, "fetch_workspace_and_branch", _fetch_workspace
    )
    monkeypatch.setattr(
        submit_task_runner.submission_service, "run_actions_tests", _run_actions_tests
    )
    monkeypatch.setattr(
        submit_task_runner.submission_service, "record_run_result", _record
    )

    (
        actions_result,
        diff_summary,
        used_workspace,
    ) = await submit_task_runner.run_code_submission(
        db=object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        payload=SimpleNamespace(workflowInputs=None, branch="main"),
        github_client=object(),
        actions_runner=object(),
    )
    assert actions_result is result
    assert diff_summary is None
    assert used_workspace is workspace
