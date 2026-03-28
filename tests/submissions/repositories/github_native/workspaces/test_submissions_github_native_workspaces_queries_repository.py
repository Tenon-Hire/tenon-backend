from __future__ import annotations

import pytest

from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_queries_repository as queries_repo,
)


class _Result:
    def __init__(self, *, first_row=None, scalar_row=None) -> None:
        self._first_row = first_row
        self._scalar_row = scalar_row

    def scalars(self):
        return self

    def first(self):
        return self._first_row

    def scalar_one_or_none(self):
        return self._scalar_row


class _FakeDB:
    def __init__(self, result: _Result) -> None:
        self._result = result
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return self._result


@pytest.mark.asyncio
async def test_get_workspace_group_returns_scalar_one_or_none_result():
    expected = object()
    db = _FakeDB(_Result(scalar_row=expected))

    found = await queries_repo.get_workspace_group(
        db,
        candidate_session_id=123,
        workspace_key="coding",
    )

    assert found is expected
    assert db.last_stmt is not None
