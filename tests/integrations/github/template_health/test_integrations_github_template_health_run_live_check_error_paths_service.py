from __future__ import annotations

import pytest

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


@pytest.mark.asyncio
async def test_run_live_check_error_paths():
    client = _LiveStubClient({"dispatch_error": GithubError("deny", status_code=403)})
    result = await template_health._run_live_check(
        client,
        repo_full_name="org/repo",
        workflow_file="wf",
        default_branch="main",
        timeout_seconds=1,
    )
    assert "github_forbidden" in result.errors
