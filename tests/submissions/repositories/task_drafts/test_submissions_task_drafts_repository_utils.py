from __future__ import annotations

from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


async def seed_context(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="task-draft-repo@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    return candidate_session, tasks[0]
