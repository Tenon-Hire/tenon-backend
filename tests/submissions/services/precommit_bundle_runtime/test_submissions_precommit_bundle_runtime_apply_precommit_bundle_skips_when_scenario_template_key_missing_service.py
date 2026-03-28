from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_apply_precommit_bundle_skips_when_scenario_template_key_missing(
    monkeypatch,
):
    async def _scenario_missing_template(_db, _scenario_version_id):
        return SimpleNamespace(template_key="")

    monkeypatch.setattr(
        precommit_service.scenario_repo, "get_by_id", _scenario_missing_template
    )
    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert result.state == "no_bundle"
