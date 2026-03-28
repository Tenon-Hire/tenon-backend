from __future__ import annotations

import pytest

from app.evaluations.repositories import (
    evaluations_repositories_evaluations_queries_repository as queries_repo,
)


class _NoExecuteDB:
    async def execute(self, _stmt):
        raise AssertionError(
            "db.execute should not be called when statuses normalize to empty"
        )


@pytest.mark.asyncio
async def test_get_latest_run_for_candidate_session_returns_none_for_empty_statuses():
    result = await queries_repo.get_latest_run_for_candidate_session(
        _NoExecuteDB(),
        candidate_session_id=123,
        statuses=[],
    )

    assert result is None
