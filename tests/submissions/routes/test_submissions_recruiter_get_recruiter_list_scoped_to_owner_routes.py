from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_list_scoped_to_owner(
    async_client, async_session: AsyncSession
):
    recruiter1 = await create_recruiter(async_session, email="owner1@test.com")
    recruiter2 = await create_recruiter(async_session, email="owner2@test.com")
    sim1, tasks1 = await create_simulation(async_session, created_by=recruiter1)
    sim2, tasks2 = await create_simulation(async_session, created_by=recruiter2)

    cs1 = await create_candidate_session(async_session, simulation=sim1)
    cs2 = await create_candidate_session(async_session, simulation=sim2)

    sub1 = await create_submission(
        async_session,
        candidate_session=cs1,
        task=tasks1[0],
        submitted_at=datetime.now(UTC),
    )
    await create_submission(
        async_session,
        candidate_session=cs2,
        task=tasks2[0],
        submitted_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        "/api/submissions",
        headers={"x-dev-user-email": recruiter1.email},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert {item["submissionId"] for item in items} == {sub1.id}
