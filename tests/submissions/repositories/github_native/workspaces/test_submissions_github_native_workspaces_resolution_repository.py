from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_resolution_repository as resolution_repo,
)


class _Result:
    def __init__(self, first_row) -> None:
        self._first_row = first_row

    def first(self):
        return self._first_row


class _FakeDB:
    def __init__(self, first_row=None) -> None:
        self._first_row = first_row
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return _Result(self._first_row)


def test_legacy_workspace_exists_expr_non_coding_key_is_literal_false():
    expr = resolution_repo._legacy_workspace_exists_expr(
        candidate_session_id=10,
        workspace_key="design",
    )

    assert expr.compare(sa.literal(False))


@pytest.mark.asyncio
async def test_workspace_key_state_returns_defaults_when_query_returns_no_row():
    db = _FakeDB(first_row=None)

    group, has_legacy_workspace = await resolution_repo._workspace_key_state(
        db,
        candidate_session_id=10,
        workspace_key="coding",
    )

    assert db.last_stmt is not None
    assert group is None
    assert has_legacy_workspace is False
