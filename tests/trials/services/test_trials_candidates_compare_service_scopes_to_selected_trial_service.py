from __future__ import annotations

import pytest

from app.trials.services import (
    trials_services_trials_candidates_compare_queries_service as compare_queries_service,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self):
        self.executed_stmt = None

    async def execute(self, stmt):
        self.executed_stmt = stmt
        return _RowsResult([])


@pytest.mark.asyncio
async def test_fetch_candidate_compare_rows_scopes_to_selected_trial():
    db = _FakeDB()

    rows = await compare_queries_service.fetch_candidate_compare_rows(db, trial_id=42)

    assert rows == []
    sql = str(db.executed_stmt).lower().replace('"', "")
    assert "join trials on trials.id = candidate_sessions.trial_id" in sql
    assert "where candidate_sessions.trial_id =" in sql
