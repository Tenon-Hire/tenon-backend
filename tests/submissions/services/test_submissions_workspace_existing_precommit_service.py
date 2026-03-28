from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_existing_service as ws_existing,
)


@pytest.mark.asyncio
async def test_ensure_existing_workspace_skips_apply_when_precommit_already_present(
    monkeypatch,
):
    existing = SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha="already-sha",
    )
    calls = {"collab": 0}

    class StubGithubClient:
        async def add_collaborator(self, repo_full_name, username):
            calls["collab"] += 1
            return {"ok": True}

    async def _get_by_session_and_task(*_args, **_kwargs):
        return existing

    async def _apply_bundle(*_args, **_kwargs):
        raise AssertionError("bundle apply should be skipped when precommit is set")

    monkeypatch.setattr(
        ws_existing.workspace_repo, "get_by_session_and_task", _get_by_session_and_task
    )
    monkeypatch.setattr(
        ws_existing, "apply_precommit_bundle_if_available", _apply_bundle
    )
    result = await ws_existing.ensure_existing_workspace(
        object(),
        candidate_session=SimpleNamespace(id=10, scenario_version_id=22),
        task=SimpleNamespace(id=5, type="code"),
        github_client=StubGithubClient(),
        github_username="octocat",
    )
    assert result is existing
    assert calls["collab"] == 1
