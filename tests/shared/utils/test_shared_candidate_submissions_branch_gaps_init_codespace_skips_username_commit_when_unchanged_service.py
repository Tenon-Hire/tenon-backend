from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_init_codespace_skips_username_commit_when_unchanged(monkeypatch):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=7, github_username="octocat")
    task = SimpleNamespace(id=99)
    workspace = SimpleNamespace(repo_full_name="acme/repo", codespace_url=None)

    def _apply_rate_limit(_session_id, _action):
        return None

    async def _validate_request(_db, _candidate_session, _task_id):
        return task

    async def _ensure_workspace(_db, **_kwargs):
        return workspace

    async def _ensure_canonical(_db, _workspace):
        return "https://codespaces.new/acme/repo?quickstart=1"

    monkeypatch.setattr(codespace_init_service, "apply_rate_limit", _apply_rate_limit)
    monkeypatch.setattr(
        codespace_init_service, "validate_codespace_request", _validate_request
    )
    monkeypatch.setattr(
        codespace_init_service.submission_service, "ensure_workspace", _ensure_workspace
    )
    monkeypatch.setattr(
        codespace_init_service,
        "ensure_canonical_workspace_url",
        _ensure_canonical,
    )
    monkeypatch.setattr(
        codespace_init_service.submission_service,
        "build_codespace_url",
        lambda repo_full_name: f"https://codespaces.new/{repo_full_name}",
    )

    (
        loaded_workspace,
        built_url,
        canonical_url,
        loaded_task,
    ) = await codespace_init_service.init_codespace(
        db,
        candidate_session=candidate_session,
        task_id=99,
        github_client=SimpleNamespace(),
        github_username="  octocat  ",
        repo_prefix="winoe-",
        template_owner=None,
        now=datetime.now(UTC),
    )

    assert loaded_workspace is workspace
    assert loaded_task is task
    assert built_url == "https://codespaces.new/acme/repo"
    assert canonical_url == "https://codespaces.new/acme/repo?quickstart=1"
    assert db.commits == 0
