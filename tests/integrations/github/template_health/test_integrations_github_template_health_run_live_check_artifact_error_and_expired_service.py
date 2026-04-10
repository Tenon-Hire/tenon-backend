from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_run_live_check_artifact_error_and_expired(monkeypatch):
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    completed_run = WorkflowRun(
        id=123,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="",
        event="workflow_dispatch",
        created_at=now_iso,
    )
    client = _LiveStubClient(
        {
            "runs": [completed_run],
            "artifact_error": GithubError("rate", status_code=429),
        }
    )
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "github_rate_limited" in result.errors

    client = _LiveStubClient(
        {
            "runs": [completed_run],
            "artifacts": [
                {
                    "name": template_health.TEST_ARTIFACT_NAMESPACE,
                    "id": 1,
                    "expired": True,
                }
            ],
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

    client = _LiveStubClient({"list_error": GithubError("rate", status_code=429)})
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "github_rate_limited" in result.errors

    client = _LiveStubClient({"runs": []})
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=0,
    )
    assert "workflow_run_timeout" in result.errors

    client = _LiveStubClient(
        {
            "runs": [completed_run],
            "artifacts": [
                {"name": template_health.LEGACY_ARTIFACT_NAME, "expired": False}
            ],
        }
    )
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "artifact_legacy_name_winoe" in result.errors
