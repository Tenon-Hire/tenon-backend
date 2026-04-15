from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_grouped_workspace_commit_false_passes_commit_and_refresh_flags(
    monkeypatch,
):
    db = _RollbackDB()
    group = SimpleNamespace(
        id="group-1",
        template_repo_full_name="org/template",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
    )
    created_workspace = SimpleNamespace(
        id="ws-new",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
        precommit_sha=None,
        precommit_details_json=None,
    )
    captured_kwargs: dict[str, object] = {}

    async def _get_or_create_group(*_args, **_kwargs):
        return group, 77

    async def _get_by_group(*_args, **_kwargs):
        return None

    async def _create_workspace(*_args, **kwargs):
        captured_kwargs.update(kwargs)
        return created_workspace

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    result = await wc._provision_grouped_workspace(
        db,
        candidate_session=SimpleNamespace(id=12),
        task=SimpleNamespace(id=34),
        workspace_key="coding",
        github_client=object(),
        github_username=None,
        repo_prefix="pref-",
        destination_owner="org",
        now=datetime.now(UTC),
        commit=False,
        hydrate_precommit_bundle=False,
    )

    assert result is created_workspace
    assert captured_kwargs["commit"] is False
    assert captured_kwargs["refresh"] is False


@pytest.mark.asyncio
async def test_provision_grouped_workspace_reraises_integrity_error_when_lookup_missing(
    monkeypatch,
):
    db = _RollbackDB()
    group = SimpleNamespace(
        id="group-1",
        template_repo_full_name="org/template",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
    )

    async def _get_or_create_group(*_args, **_kwargs):
        return group, 77

    async def _get_by_group(*_args, **_kwargs):
        return None

    async def _create_workspace(*_args, **_kwargs):
        raise IntegrityError("", {}, None)

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    with pytest.raises(IntegrityError):
        await wc._provision_grouped_workspace(
            db,
            candidate_session=SimpleNamespace(id=12),
            task=SimpleNamespace(id=34),
            workspace_key="coding",
            github_client=object(),
            github_username="octocat",
            repo_prefix="pref-",
            destination_owner="org",
            now=datetime.now(UTC),
        )

    assert db.rollback_calls == 1
