from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_non_group_path_bootstraps_empty_repo(monkeypatch):
    db = object()
    candidate_session = SimpleNamespace(id=11)
    trial = SimpleNamespace(id=7, title="Trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        id=88,
        storyline_md="# From scratch",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nBuild from scratch.\n"
            "\n## System Requirements\n\nCreate the repo baseline.\n"
            "\n## Deliverables\n\n- Empty repo only.\n"
        ),
    )
    task = SimpleNamespace(id=101, day_index=1, type="design")
    now = datetime.now(UTC)
    github_client = object()
    calls: dict[str, object] = {}
    created = SimpleNamespace(
        id="ws-1",
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
    )

    async def _get_or_create_workspace_group(*_args, **_kwargs):
        raise AssertionError("grouped path should not be used")

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return False

    async def _bootstrap_empty_candidate_repo(**kwargs):
        calls["bootstrap"] = kwargs
        return SimpleNamespace(
            template_repo_full_name=None,
            repo_full_name="org/repo",
            default_branch="main",
            repo_id=123,
            bootstrap_commit_sha="base-sha",
            codespace_name="codespace-1",
            codespace_state="available",
            codespace_url="https://codespace-1.github.dev",
        )

    async def _add_collaborator_if_needed(_client, _repo, _username):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return created

    monkeypatch.setattr(
        wc, "_get_or_create_workspace_group", _get_or_create_workspace_group
    )
    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(
        wc._single_module,
        "bootstrap_empty_candidate_repo",
        _bootstrap_empty_candidate_repo,
    )
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    result = await wc.provision_workspace(
        db,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=task,
        github_client=github_client,
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=now,
        bootstrap_empty_repo=True,
        hydrate_precommit_bundle=False,
    )

    assert result is created
    assert calls["collaborator"] is True
    assert calls["bootstrap"]["candidate_session"] is candidate_session
    assert calls["create_workspace"] == {
        "candidate_session_id": candidate_session.id,
        "task_id": task.id,
        "template_repo_full_name": None,
        "repo_full_name": "org/repo",
        "repo_id": 123,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "codespace_url": "https://codespace-1.github.dev",
        "codespace_name": "codespace-1",
        "codespace_state": "available",
        "created_at": now,
    }
