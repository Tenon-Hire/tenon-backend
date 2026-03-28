from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_creation_single_service as workspace_creation_single,
)


@pytest.mark.asyncio
async def test_provision_single_workspace_returns_early_when_hydration_disabled(
    monkeypatch,
):
    calls: dict[str, object] = {}
    workspace = SimpleNamespace(id="ws-1")

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/repo", "main", 123)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

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
        workspace_creation_single, "generate_template_repo", _generate_template_repo
    )
    monkeypatch.setattr(
        workspace_creation_single, "fetch_base_template_sha", _fetch_base_template_sha
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
        task=SimpleNamespace(id=101),
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime(2026, 3, 26, tzinfo=UTC),
        commit=False,
        hydrate_precommit_bundle=False,
    )

    assert result is workspace
    assert calls["collaborator"] is True
    assert calls["create_workspace"]["commit"] is False
    assert calls["create_workspace"]["refresh"] is False
