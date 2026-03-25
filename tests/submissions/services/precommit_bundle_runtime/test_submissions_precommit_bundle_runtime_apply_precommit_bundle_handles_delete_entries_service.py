from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_apply_precommit_bundle_handles_delete_entries(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=14,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "obsolete.txt", "delete": True}]}
            ),
            storage_ref=None,
        )

    github_client = _BranchFailureGithub(commits_by_call=[[]])
    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=github_client,
        candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert result.state == "applied"
    assert github_client.created_blobs == []
