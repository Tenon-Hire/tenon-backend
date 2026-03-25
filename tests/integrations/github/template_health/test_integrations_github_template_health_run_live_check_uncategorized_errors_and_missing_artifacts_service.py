from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_run_live_check_uncategorized_errors_and_missing_artifacts():
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    completed_run = WorkflowRun(
        id=99,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="",
        event="workflow_dispatch",
        created_at=now_iso,
    )
    client = _LiveStubClient({"list_error": GithubError("boom")})
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "workflow_dispatch_failed" in result.errors

    client = _LiveStubClient(
        {
            "runs": [completed_run],
            "artifacts": [{"name": template_health.TEST_ARTIFACT_NAMESPACE}],
        }
    )
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "artifact_missing" in result.errors

    client = _LiveStubClient(
        {
            "runs": [completed_run],
            "artifacts": [{"name": template_health.TEST_ARTIFACT_NAMESPACE, "id": 5}],
            "download_error": GithubError("nope", status_code=403),
        }
    )
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "github_forbidden" in result.errors
