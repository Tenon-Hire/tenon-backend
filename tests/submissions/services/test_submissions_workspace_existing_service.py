from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_existing_service as ws_existing,
)


def test_serialize_no_bundle_details_handles_non_matching_inputs():
    assert (
        ws_existing._serialize_no_bundle_details(
            SimpleNamespace(state="applied", details={"reason": "commit_created"})
        )
        is None
    )
    assert (
        ws_existing._serialize_no_bundle_details(
            SimpleNamespace(state="no_bundle", details=["bad-payload"])
        )
        is None
    )


@pytest.mark.asyncio
async def test_ensure_existing_workspace_hydrates_missing_precommit(monkeypatch):
    existing = SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
    )
    calls: dict[str, str] = {}

    async def _get_by_session_and_task(*_args, **_kwargs):
        return existing

    async def _apply_bundle(*_args, **_kwargs):
        return SimpleNamespace(
            state="applied", precommit_sha="precommit-sha", bundle_id=1
        )

    async def _set_precommit_sha(_db, *, workspace, precommit_sha):
        calls["precommit"] = precommit_sha
        workspace.precommit_sha = precommit_sha
        return workspace

    monkeypatch.setattr(
        ws_existing.workspace_repo, "get_by_session_and_task", _get_by_session_and_task
    )
    monkeypatch.setattr(
        ws_existing, "apply_precommit_bundle_if_available", _apply_bundle
    )
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_sha", _set_precommit_sha
    )
    result = await ws_existing.ensure_existing_workspace(
        object(),
        candidate_session=SimpleNamespace(id=10, scenario_version_id=22),
        task=SimpleNamespace(id=5, type="code"),
        github_client=object(),
        github_username=None,
    )
    assert result is existing
    assert calls["precommit"] == "precommit-sha"
    assert existing.precommit_sha == "precommit-sha"


@pytest.mark.asyncio
async def test_ensure_existing_workspace_hydrates_precommit_without_commit(monkeypatch):
    existing = SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
        precommit_details_json=None,
    )
    calls: dict[str, object] = {}

    async def _get_by_session_and_task(*_args, **_kwargs):
        return existing

    async def _apply_bundle(*_args, **_kwargs):
        return SimpleNamespace(
            state="applied", precommit_sha="precommit-nocommit", bundle_id=5
        )

    async def _set_precommit_sha(
        _db,
        *,
        workspace,
        precommit_sha,
        commit=True,
        refresh=True,
    ):
        calls["precommit_sha"] = precommit_sha
        calls["commit"] = commit
        calls["refresh"] = refresh
        workspace.precommit_sha = precommit_sha
        return workspace

    monkeypatch.setattr(
        ws_existing.workspace_repo, "get_by_session_and_task", _get_by_session_and_task
    )
    monkeypatch.setattr(
        ws_existing, "apply_precommit_bundle_if_available", _apply_bundle
    )
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_sha", _set_precommit_sha
    )

    result = await ws_existing.ensure_existing_workspace(
        object(),
        candidate_session=SimpleNamespace(id=10, scenario_version_id=22),
        task=SimpleNamespace(id=5, type="code"),
        github_client=object(),
        github_username=None,
        commit=False,
    )

    assert result is existing
    assert calls == {
        "precommit_sha": "precommit-nocommit",
        "commit": False,
        "refresh": False,
    }
