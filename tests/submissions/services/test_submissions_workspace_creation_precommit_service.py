from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_creation_precommit_service as precommit_service,
)


@pytest.mark.asyncio
async def test_persist_precommit_result_sets_precommit_sha_without_commit(monkeypatch):
    workspace = SimpleNamespace(precommit_sha=None, precommit_details_json=None)
    calls: dict[str, object] = {}

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
        precommit_service.workspace_repo, "set_precommit_sha", _set_precommit_sha
    )

    result = await precommit_service.persist_precommit_result(
        object(),
        workspace=workspace,
        precommit_result=SimpleNamespace(
            precommit_sha="precommit-123",
            state="applied",
            details=None,
        ),
        commit=False,
    )

    assert result is workspace
    assert calls == {
        "precommit_sha": "precommit-123",
        "commit": False,
        "refresh": False,
    }


@pytest.mark.asyncio
async def test_persist_precommit_result_sets_no_bundle_details_without_commit(
    monkeypatch,
):
    workspace = SimpleNamespace(precommit_sha=None, precommit_details_json=None)
    calls: dict[str, object] = {}

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
        precommit_service.workspace_repo,
        "set_precommit_details",
        _set_precommit_details,
    )

    result = await precommit_service.persist_precommit_result(
        object(),
        workspace=workspace,
        precommit_result=SimpleNamespace(
            precommit_sha=None,
            state="no_bundle",
            details={"reason": "bundle_not_found", "templateKey": "default"},
        ),
        commit=False,
    )

    assert result is workspace
    assert calls["commit"] is False
    assert calls["refresh"] is False
    assert json.loads(calls["precommit_details_json"]) == {
        "reason": "bundle_not_found",
        "state": "no_bundle",
        "templateKey": "default",
    }
