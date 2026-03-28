from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_progress_loaders_service as progress_loaders,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.executed_stmt = None

    async def execute(self, stmt):
        self.executed_stmt = stmt
        return _RowsResult(self._rows)


@pytest.mark.asyncio
async def test_load_tasks_with_completion_state_skips_none_submission_ids():
    task_one = SimpleNamespace(id=10, day_index=2)
    task_two = SimpleNamespace(id=11, day_index=3)
    db = _FakeDB(
        rows=[
            (task_one, None),
            (task_one, 555),
            (task_two, None),
        ]
    )

    tasks, completed_ids = await progress_loaders.load_tasks_with_completion_state(
        db,
        simulation_id=123,
        candidate_session_id=456,
    )

    assert db.executed_stmt is not None
    assert [task.id for task in tasks] == [10, 11]
    assert completed_ids == {10}
