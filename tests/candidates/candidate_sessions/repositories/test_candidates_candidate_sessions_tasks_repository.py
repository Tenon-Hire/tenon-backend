from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.candidates.candidate_sessions.repositories import (
    candidates_candidate_sessions_repositories_candidates_candidate_sessions_tasks_repository as tasks_repo,
)


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _FakeExecuteResult:
    def __init__(self, *, scalar_values=None, rows=None):
        self._scalar_values = scalar_values or []
        self._rows = rows or []

    def scalars(self):
        return _FakeScalars(self._scalar_values)

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self, result: _FakeExecuteResult):
        self._result = result
        self.executed_stmt = None

    async def execute(self, stmt):
        self.executed_stmt = stmt
        return self._result


@pytest.mark.asyncio
async def test_tasks_for_trial_returns_task_scalars():
    task_one = SimpleNamespace(id=1, day_index=1)
    task_two = SimpleNamespace(id=2, day_index=2)
    db = _FakeDB(_FakeExecuteResult(scalar_values=[task_one, task_two]))

    result = await tasks_repo.tasks_for_trial(db, trial_id=10)

    assert result == [task_one, task_two]
    assert db.executed_stmt is not None


@pytest.mark.asyncio
async def test_completed_task_ids_returns_distinct_set():
    db = _FakeDB(_FakeExecuteResult(scalar_values=[1, 1, 2, 2]))

    result = await tasks_repo.completed_task_ids(db, candidate_session_id=20)

    assert result == {1, 2}
    assert db.executed_stmt is not None


@pytest.mark.asyncio
async def test_completed_task_ids_bulk_returns_empty_for_empty_input():
    result = await tasks_repo.completed_task_ids_bulk(object(), [])
    assert result == {}


@pytest.mark.asyncio
async def test_completed_task_ids_bulk_filters_none_rows_and_deduplicates():
    db = _FakeDB(
        _FakeExecuteResult(
            rows=[
                (10, 101),
                (10, 101),
                (10, None),
                (None, 303),
                (11, 202),
            ]
        )
    )

    result = await tasks_repo.completed_task_ids_bulk(db, [10, 11, 12])

    assert result == {
        10: {101},
        11: {202},
        12: set(),
    }
    assert db.executed_stmt is not None
