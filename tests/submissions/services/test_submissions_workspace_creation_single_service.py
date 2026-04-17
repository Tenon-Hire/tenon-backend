from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_creation_single_service as workspace_creation_single,
)


@pytest.mark.asyncio
async def test_provision_single_workspace_bootstraps_empty_repo(
    monkeypatch,
):
    calls: dict[str, object] = {}
    workspace = SimpleNamespace(id="ws-1")
    trial = SimpleNamespace(title="Trial title", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Build from scratch",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nBuild from scratch.\n"
            "\n## System Requirements\n\nBuild the workspace baseline.\n"
            "\n## Deliverables\n\n- Repo stays empty except bootstrap files.\n"
        ),
    )

    async def _bootstrap_empty_candidate_repo(**kwargs):
        calls["bootstrap"] = kwargs
        return SimpleNamespace(
            template_repo_full_name=None,
            repo_full_name="org/repo",
            default_branch="main",
            repo_id=123,
            bootstrap_commit_sha="base-sha",
            codespace_name="codespace-123",
            codespace_state="available",
            codespace_url="https://codespace-123.github.dev",
        )

    async def _add_collaborator_if_needed(*_args, **_kwargs):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return workspace

    async def _apply_precommit_bundle(*_args, **_kwargs):
        raise AssertionError("precommit hydration should be skipped")

    async def _persist_precommit_result(*_args, **_kwargs):
        raise AssertionError("persist_precommit_result should not be called")

    monkeypatch.setattr(
        workspace_creation_single,
        "bootstrap_empty_candidate_repo",
        _bootstrap_empty_candidate_repo,
    )
    monkeypatch.setattr(
        workspace_creation_single,
        "add_collaborator_if_needed",
        _add_collaborator_if_needed,
    )
    monkeypatch.setattr(
        workspace_creation_single.workspace_repo, "create_workspace", _create_workspace
    )
    monkeypatch.setattr(
        workspace_creation_single,
        "apply_precommit_bundle_if_available",
        _apply_precommit_bundle,
    )
    monkeypatch.setattr(
        workspace_creation_single, "persist_precommit_result", _persist_precommit_result
    )

    result = await workspace_creation_single.provision_single_workspace(
        db=object(),
        candidate_session=SimpleNamespace(id=11),
        trial=trial,
        scenario_version=scenario_version,
        task=SimpleNamespace(id=101, title="Day 2 coding"),
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=datetime(2026, 3, 26, tzinfo=UTC),
        commit=False,
        hydrate_precommit_bundle=False,
        bootstrap_empty_repo=True,
    )

    assert result is workspace
    assert calls["collaborator"] is True
    assert calls["bootstrap"]["candidate_session"].id == 11
    assert calls["bootstrap"]["trial"] is trial
    assert calls["bootstrap"]["scenario_version"] is scenario_version
    assert calls["create_workspace"] == {
        "candidate_session_id": 11,
        "task_id": 101,
        "template_repo_full_name": None,
        "repo_full_name": "org/repo",
        "repo_id": 123,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "codespace_url": "https://codespace-123.github.dev",
        "codespace_name": "codespace-123",
        "codespace_state": "available",
        "created_at": datetime(2026, 3, 26, tzinfo=UTC),
        "commit": False,
        "refresh": False,
    }
