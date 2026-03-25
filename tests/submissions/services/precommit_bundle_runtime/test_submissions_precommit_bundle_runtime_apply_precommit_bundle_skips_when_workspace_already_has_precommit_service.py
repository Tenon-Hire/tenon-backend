from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_apply_precommit_bundle_skips_when_workspace_already_has_precommit():
    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=2),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha="already-sha",
    )
    assert result.state == "already_applied"
    assert result.precommit_sha == "already-sha"
