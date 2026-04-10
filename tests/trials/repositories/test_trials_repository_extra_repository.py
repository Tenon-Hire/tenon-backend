import pytest

from app.trials.repositories import repository as sim_repo


@pytest.mark.asyncio
async def test_trials_repository_empty_paths(async_session):
    # list_with_candidate_counts with no data should still return iterable
    rows = await sim_repo.list_with_candidate_counts(async_session, user_id=0)
    assert list(rows) == []

    sim, tasks = await sim_repo.get_owned_with_tasks(async_session, 1, 1)
    assert sim is None and tasks == []


@pytest.mark.asyncio
async def test_trials_repository_with_tasks(async_session):
    # Create a simple trial with one task to ensure tasks are returned.
    from tests.shared.factories import create_talent_partner, create_trial

    talent_partner = await create_talent_partner(async_session, email="repo@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)

    found_sim, found_tasks = await sim_repo.get_owned_with_tasks(
        async_session, sim.id, talent_partner.id
    )
    assert found_sim.id == sim.id
    assert [t.id for t in found_tasks] == [t.id for t in tasks]
