from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_existing_service as ws_existing,
)


@pytest.mark.asyncio
async def test_ensure_existing_workspace_records_no_bundle_details(monkeypatch):
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
            state="no_bundle",
            precommit_sha=None,
            bundle_id=None,
            details={
                "reason": "bundle_not_found",
                "scenarioVersionId": 22,
                "templateKey": "template-default",
            },
        )

    async def _set_precommit_sha(*_args, **_kwargs):
        raise AssertionError("precommit_sha should stay null on no_bundle")

    async def _set_precommit_details(_db, *, workspace, precommit_details_json):
        calls["precommit_details_json"] = precommit_details_json
        workspace.precommit_details_json = precommit_details_json
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
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_details", _set_precommit_details
    )
    result = await ws_existing.ensure_existing_workspace(
        object(),
        candidate_session=SimpleNamespace(id=10, scenario_version_id=22),
        task=SimpleNamespace(id=5, type="code"),
        github_client=object(),
        github_username=None,
    )
    assert result is existing
    assert result.precommit_sha is None
    assert json.loads(calls["precommit_details_json"]) == {
        "reason": "bundle_not_found",
        "scenarioVersionId": 22,
        "state": "no_bundle",
        "templateKey": "template-default",
    }


@pytest.mark.asyncio
async def test_ensure_existing_workspace_returns_existing_when_no_updates(monkeypatch):
    stable_details = json.dumps({"reason": "bundle_not_found", "state": "no_bundle"})
    existing = SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
        precommit_details_json=stable_details,
    )

    async def _get_by_session_and_task(*_args, **_kwargs):
        return existing

    async def _apply_bundle(*_args, **_kwargs):
        return SimpleNamespace(
            state="no_bundle",
            precommit_sha=None,
            bundle_id=None,
            details={"reason": "bundle_not_found"},
        )

    async def _set_precommit_sha(*_args, **_kwargs):
        raise AssertionError("precommit_sha should not be updated")

    async def _set_precommit_details(*_args, **_kwargs):
        raise AssertionError("precommit_details_json should not be updated")

    monkeypatch.setattr(
        ws_existing.workspace_repo, "get_by_session_and_task", _get_by_session_and_task
    )
    monkeypatch.setattr(
        ws_existing, "apply_precommit_bundle_if_available", _apply_bundle
    )
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_sha", _set_precommit_sha
    )
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_details", _set_precommit_details
    )
    result = await ws_existing.ensure_existing_workspace(
        object(),
        candidate_session=SimpleNamespace(id=10, scenario_version_id=22),
        task=SimpleNamespace(id=5, type="code"),
        github_client=object(),
        github_username=None,
    )
    assert result is existing


@pytest.mark.asyncio
async def test_ensure_existing_workspace_sets_no_bundle_details_without_commit(
    monkeypatch,
):
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
            state="no_bundle",
            precommit_sha=None,
            bundle_id=None,
            details={"reason": "bundle_not_found"},
        )

    async def _set_precommit_details(
        _db,
        *,
        workspace,
        precommit_details_json,
        commit=True,
        refresh=True,
    ):
        calls["precommit_details_json"] = precommit_details_json
        calls["commit"] = commit
        calls["refresh"] = refresh
        workspace.precommit_details_json = precommit_details_json
        return workspace

    monkeypatch.setattr(
        ws_existing.workspace_repo, "get_by_session_and_task", _get_by_session_and_task
    )
    monkeypatch.setattr(
        ws_existing, "apply_precommit_bundle_if_available", _apply_bundle
    )
    monkeypatch.setattr(
        ws_existing.workspace_repo, "set_precommit_details", _set_precommit_details
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
    assert calls["commit"] is False
    assert calls["refresh"] is False
    assert json.loads(calls["precommit_details_json"]) == {
        "reason": "bundle_not_found",
        "state": "no_bundle",
    }
