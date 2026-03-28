from __future__ import annotations

import pytest

from app.simulations.repositories.scenario_versions import (
    simulations_repositories_scenario_versions_simulations_scenario_versions_repository as scenario_versions_repo,
)


class _Result:
    def __init__(self, scalar) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class _FakeDB:
    def __init__(self, scalar) -> None:
        self._scalar = scalar
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return _Result(self._scalar)


@pytest.mark.asyncio
async def test_get_active_for_simulation_for_update_applies_row_lock():
    sentinel = object()
    db = _FakeDB(sentinel)

    result = await scenario_versions_repo.get_active_for_simulation(
        db, simulation_id=42, for_update=True
    )

    assert result is sentinel
    assert db.last_stmt is not None
    assert db.last_stmt._for_update_arg is not None
