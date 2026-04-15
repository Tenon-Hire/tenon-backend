from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_handles_duplicate_insert(monkeypatch):
    db = _RollbackDB()
    existing = SimpleNamespace(repo_full_name="org/coding")
    lookup_calls = {"count": 0}
    calls: list[tuple[str, str, str | None]] = []

    async def _get_workspace_group(*_args, **_kwargs):
        lookup_calls["count"] += 1
        return None if lookup_calls["count"] == 1 else existing

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/coding", "main", 42)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _add_collaborator_if_needed(_client, repo, username):
        calls.append(("collab", repo, username))

    async def _create_workspace_group(*_args, **_kwargs):
        raise IntegrityError("", {}, None)

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(
        wc.workspace_repo, "create_workspace_group", _create_workspace_group
    )

    group, repo_id = await wc._get_or_create_workspace_group(
        db,
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=datetime.now(UTC),
    )

    assert group is existing
    assert repo_id is None
    assert db.rollback_calls == 1
    assert calls == [
        ("collab", "org/coding", "octocat"),
        ("collab", "org/coding", "octocat"),
    ]


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_raises_when_duplicate_recovery_lookup_missing(
    monkeypatch,
):
    db = _RollbackDB()

    async def _get_workspace_group(*_args, **_kwargs):
        return None

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/coding", "main", 42)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _create_workspace_group(*_args, **_kwargs):
        raise IntegrityError("", {}, None)

    async def _add_collaborator_if_needed(*_args, **_kwargs):
        return None

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(
        wc.workspace_repo, "create_workspace_group", _create_workspace_group
    )
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)

    with pytest.raises(IntegrityError):
        await wc._get_or_create_workspace_group(
            db,
            candidate_session=SimpleNamespace(id=1),
            task=SimpleNamespace(id=2),
            workspace_key="coding",
            github_client=object(),
            github_username="octocat",
            repo_prefix="pref-",
            destination_owner="org",
            now=datetime.now(UTC),
        )

    assert db.rollback_calls == 1
