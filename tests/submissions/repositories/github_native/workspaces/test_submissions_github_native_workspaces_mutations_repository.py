from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_mutations_repository as mutations_repo,
)


class _FakeDB:
    def __init__(self) -> None:
        self.added = []
        self.commit_calls = 0
        self.flush_calls = 0
        self.refresh_calls = 0

    def add(self, model) -> None:
        self.added.append(model)

    async def commit(self) -> None:
        self.commit_calls += 1

    async def flush(self) -> None:
        self.flush_calls += 1

    async def refresh(self, _model) -> None:
        self.refresh_calls += 1


@pytest.mark.asyncio
async def test_create_workspace_group_refresh_false_skips_refresh():
    db = _FakeDB()
    group = await mutations_repo.create_workspace_group(
        db,
        candidate_session_id=1,
        workspace_key="coding",
        template_repo_full_name="org/template",
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base",
        created_at=datetime(2026, 3, 20, tzinfo=UTC),
        commit=True,
        refresh=False,
    )

    assert db.added == [group]
    assert db.commit_calls == 1
    assert db.flush_calls == 0
    assert db.refresh_calls == 0


@pytest.mark.asyncio
async def test_create_workspace_refresh_false_skips_refresh():
    db = _FakeDB()
    workspace = await mutations_repo.create_workspace(
        db,
        candidate_session_id=1,
        task_id=2,
        workspace_group_id="wg-1",
        template_repo_full_name="org/template",
        repo_full_name="org/repo",
        repo_id=101,
        default_branch="main",
        base_template_sha="base",
        created_at=datetime(2026, 3, 21, tzinfo=UTC),
        commit=True,
        refresh=False,
    )

    assert db.added == [workspace]
    assert db.commit_calls == 1
    assert db.flush_calls == 0
    assert db.refresh_calls == 0


@pytest.mark.asyncio
async def test_set_precommit_details_refresh_false_skips_refresh():
    db = _FakeDB()
    workspace = SimpleNamespace(precommit_details_json=None)

    updated = await mutations_repo.set_precommit_details(
        db,
        workspace=workspace,
        precommit_details_json='{"applied": false}',
        commit=True,
        refresh=False,
    )

    assert updated is workspace
    assert workspace.precommit_details_json == '{"applied": false}'
    assert db.commit_calls == 1
    assert db.flush_calls == 0
    assert db.refresh_calls == 0
