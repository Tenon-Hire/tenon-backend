from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.submissions.exceptions import WorkspaceMissing
from app.integrations.github.client import GithubError
from app.services.submissions import workspace_creation as wc


class _RollbackDB:
    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.mark.asyncio
async def test_provision_workspace_non_group_path(monkeypatch):
    db = object()
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=1, type="design")
    now = datetime.now(UTC)
    github_client = object()
    calls: dict[str, object] = {}
    created = SimpleNamespace(id="ws-1")

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/repo", "main", 123)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _add_collaborator_if_needed(_client, _repo, _username):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return created

    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    result = await wc.provision_workspace(
        db,
        candidate_session=candidate_session,
        task=task,
        github_client=github_client,
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=now,
    )

    assert result is created
    assert calls["collaborator"] is True
    assert calls["create_workspace"] == {
        "candidate_session_id": candidate_session.id,
        "task_id": task.id,
        "template_repo_full_name": "org/template",
        "repo_full_name": "org/repo",
        "repo_id": 123,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_provision_workspace_coding_task_uses_grouped_path_when_eligible(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=2, type="code")
    created = SimpleNamespace(id="ws-grouped")
    calls: dict[str, int] = {"grouped": 0}

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return True

    async def _provision_grouped_workspace(*_args, **_kwargs):
        calls["grouped"] += 1
        return created

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(
        wc, "_provision_grouped_workspace", _provision_grouped_workspace
    )

    result = await wc.provision_workspace(
        object(),
        candidate_session=candidate_session,
        task=task,
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert result is created
    assert calls["grouped"] == 1


@pytest.mark.asyncio
async def test_provision_workspace_day3_requires_existing_coding_group(monkeypatch):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=3, type="debug")

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return True

    async def _get_workspace_group(*_args, **_kwargs):
        return None

    async def _provision_grouped_workspace(*_args, **_kwargs):
        raise AssertionError("Day 3 init should not create a new grouped repo")

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(
        wc, "_provision_grouped_workspace", _provision_grouped_workspace
    )

    with pytest.raises(WorkspaceMissing) as excinfo:
        await wc.provision_workspace(
            object(),
            candidate_session=candidate_session,
            task=task,
            github_client=object(),
            github_username="octocat",
            repo_prefix="pref-",
            template_default_owner="org",
            now=datetime.now(UTC),
        )

    assert excinfo.value.error_code == "WORKSPACE_NOT_INITIALIZED"


@pytest.mark.asyncio
async def test_provision_workspace_coding_task_uses_legacy_path_when_grouping_disabled(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=2, type="code")
    now = datetime.now(UTC)
    calls: dict[str, object] = {}
    created = SimpleNamespace(id="ws-legacy")

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return False

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/day3", "main", 456)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _add_collaborator_if_needed(_client, _repo, _username):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return created

    async def _provision_grouped_workspace(*_args, **_kwargs):
        raise AssertionError("Grouped path should be skipped for legacy sessions")

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)
    monkeypatch.setattr(
        wc, "_provision_grouped_workspace", _provision_grouped_workspace
    )

    result = await wc.provision_workspace(
        object(),
        candidate_session=candidate_session,
        task=task,
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=now,
    )

    assert result is created
    assert calls["collaborator"] is True
    assert calls["create_workspace"] == {
        "candidate_session_id": candidate_session.id,
        "task_id": task.id,
        "template_repo_full_name": "org/template",
        "repo_full_name": "org/day3",
        "repo_id": 456,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_provision_grouped_workspace_reuses_existing_group_workspace(monkeypatch):
    existing = SimpleNamespace(id="ws-existing", repo_full_name="org/coding")
    group = SimpleNamespace(
        id="group-1",
        template_repo_full_name="org/template",
        repo_full_name="org/coding",
        default_branch="main",
        base_template_sha="base",
    )
    calls: list[tuple[str, str, str | None]] = []

    async def _get_or_create_group(*_args, **_kwargs):
        return group, None

    async def _get_by_group(*_args, **_kwargs):
        return existing

    async def _add_collaborator_if_needed(_client, repo, username):
        calls.append(("collab", repo, username))

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)

    result = await wc._provision_grouped_workspace(
        object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert result is existing
    assert calls == [("collab", "org/coding", "octocat")]


@pytest.mark.asyncio
async def test_provision_grouped_workspace_handles_duplicate_workspace_row(monkeypatch):
    db = _RollbackDB()
    fallback = SimpleNamespace(id="ws-fallback")
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

    monkeypatch.setattr(wc, "_get_or_create_workspace_group", _get_or_create_group)
    monkeypatch.setattr(wc.workspace_repo, "get_by_workspace_group_id", _get_by_group)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    result = await wc._provision_grouped_workspace(
        db,
        candidate_session=SimpleNamespace(id=12),
        task=SimpleNamespace(id=34),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert result is fallback
    assert db.rollback_calls == 1
    assert lookup_calls["count"] == 2


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_reuses_existing(monkeypatch):
    existing = SimpleNamespace(repo_full_name="org/coding")
    calls: list[tuple[str, str, str | None]] = []

    async def _get_workspace_group(*_args, **_kwargs):
        return existing

    async def _add_collaborator_if_needed(_client, repo, username):
        calls.append(("collab", repo, username))

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)

    group, repo_id = await wc._get_or_create_workspace_group(
        object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert group is existing
    assert repo_id is None
    assert calls == [("collab", "org/coding", "octocat")]


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_handles_422_conflict(monkeypatch):
    existing = SimpleNamespace(repo_full_name="org/coding")
    calls: list[tuple[str, str, str | None]] = []
    lookup_calls = {"count": 0}

    async def _get_workspace_group(*_args, **_kwargs):
        lookup_calls["count"] += 1
        return None if lookup_calls["count"] == 1 else existing

    async def _generate_template_repo(**_kwargs):
        raise GithubError("already exists", status_code=422)

    async def _add_collaborator_if_needed(_client, repo, username):
        calls.append(("collab", repo, username))

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)

    group, repo_id = await wc._get_or_create_workspace_group(
        object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert group is existing
    assert repo_id is None
    assert calls == [("collab", "org/coding", "octocat")]


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
        template_default_owner="org",
        now=datetime.now(UTC),
    )

    assert group is existing
    assert repo_id is None
    assert db.rollback_calls == 1
    assert calls == [
        ("collab", "org/coding", "octocat"),
        ("collab", "org/coding", "octocat"),
    ]
