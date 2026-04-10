from __future__ import annotations

import pytest

from app.tasks.repositories import (
    tasks_repositories_tasks_lookup_repository as tasks_repository,
)
from tests.shared.factories import create_talent_partner, create_trial


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(async_session):
    result = await tasks_repository.get_by_id(async_session, 9999)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_task(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="taskrepo@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = tasks[0]
    found = await tasks_repository.get_by_id(async_session, task.id)
    assert found.id == task.id
