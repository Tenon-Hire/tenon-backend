from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_repository_owned_for_update_and_include_terminated_filter(async_session):
    recruiter = await create_recruiter(async_session, email="owned-filter@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)

    owned = await repository_owned.get_owned(
        async_session,
        simulation.id,
        recruiter.id,
        for_update=True,
    )
    assert owned is not None

    simulation.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()

    filtered_sim, filtered_tasks = await repository_owned.get_owned_with_tasks(
        async_session,
        simulation.id,
        recruiter.id,
        include_terminated=False,
    )
    assert filtered_sim is None
    assert filtered_tasks == []
