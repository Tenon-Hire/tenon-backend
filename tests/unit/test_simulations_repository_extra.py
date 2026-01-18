import pytest

from app.domains.simulations import repository as sim_repo


@pytest.mark.asyncio
async def test_simulations_repository_empty_paths(async_session):
    # list_with_candidate_counts with no data should still return iterable
    rows = await sim_repo.list_with_candidate_counts(async_session, user_id=0)
    assert list(rows) == []

    sim, tasks = await sim_repo.get_owned_with_tasks(async_session, 1, 1)
    assert sim is None and tasks == []
