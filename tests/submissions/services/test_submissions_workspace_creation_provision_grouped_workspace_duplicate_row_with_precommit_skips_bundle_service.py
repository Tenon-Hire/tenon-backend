from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_grouped_workspace_duplicate_row_with_precommit_skips_bundle(
    monkeypatch,
):
    db = _RollbackDB()
    fallback = SimpleNamespace(
        id="ws-fallback",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
        precommit_sha="existing-precommit-sha",
    )
    group = SimpleNamespace(
        id="group-1",
        template_repo_full_name="org/template",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
    )

    async def _get_or_create_group(*_args, **_kwargs):
        return group, 77

    lookup_calls = {"count": 0}

    async def _get_by_group(*_args, **_kwargs):
        lookup_calls["count"] += 1
        return None if lookup_calls["count"] == 1 else fallback

    async def _create_workspace(*_args, **_kwargs):
        raise IntegrityError("", {}, None)

    async def _apply_bundle(*_args, **_kwargs):
        raise AssertionError("bundle apply should be skipped when precommit is set")

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)
    monkeypatch.setattr(wc, "apply_precommit_bundle_if_available", _apply_bundle)

    result = await wc._provision_grouped_workspace(
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

    assert result is fallback
    assert db.rollback_calls == 1
    assert lookup_calls["count"] == 2
