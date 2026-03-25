from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_build_result_sets_raw_when_missing(monkeypatch):
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )

    async def _fake_parse(repo, run_id):
        return (
            ParsedTestResults(
                passed=1,
                failed=0,
                total=1,
                stdout="o",
                stderr=None,
                summary={"ok": True},
            ),
            None,
        )

    monkeypatch.setattr(runner, "_parse_artifacts", _fake_parse)

    # Force _normalize_run to omit raw so branch is covered
    def _no_raw(run, **_kw):
        return ActionsRunResult(
            status="passed",
            run_id=run.id,
            conclusion="success",
            passed=None,
            failed=None,
            total=None,
            stdout=None,
            stderr=None,
            head_sha=run.head_sha,
            html_url=run.html_url,
            raw=None,
        )

    monkeypatch.setattr(runner, "_normalize_run", _no_raw)

    # Provide a run with no artifacts to keep raw None
    run = WorkflowRun(
        id=7,
        status="completed",
        conclusion="success",
        html_url="url",
        head_sha="sha",
        artifact_count=None,
    )
    result = await runner._build_result("org/repo", run)
    assert result.raw and result.raw["summary"]["ok"] is True
    assert result.status == "passed"
