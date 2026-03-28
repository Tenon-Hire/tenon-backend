from __future__ import annotations

from tests.shared.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


async def seed_context(async_session):
    recruiter = await create_recruiter(async_session, email="task-draft-repo@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    return candidate_session, tasks[0]
