from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_grouped_workspace_skips_bundle_apply_when_precommit_present(
    monkeypatch,
):
    existing = SimpleNamespace(
        id="ws-existing",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
        precommit_sha="already-sha",
    )
    group = SimpleNamespace(
        id="group-1",
        template_repo_full_name="org/template",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
    )

    async def _get_or_create_group(*_args, **_kwargs):
        return group, None

    async def _get_by_group(*_args, **_kwargs):
        return existing

    async def _add_collaborator_if_needed(*_args, **_kwargs):
        return None

    async def _apply_bundle(*_args, **_kwargs):
        raise AssertionError("bundle apply should be skipped when precommit is set")

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc, "apply_precommit_bundle_if_available", _apply_bundle)

    result = await wc._provision_grouped_workspace(
        object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=datetime.now(UTC),
    )

    assert result is existing
    assert result.precommit_sha == "already-sha"
