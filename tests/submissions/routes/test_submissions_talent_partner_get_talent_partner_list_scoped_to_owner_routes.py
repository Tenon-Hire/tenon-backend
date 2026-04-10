from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_list_scoped_to_owner(
    async_client, async_session: AsyncSession
):
    talent_partner1 = await create_talent_partner(
        async_session, email="owner1@test.com"
    )
    talent_partner2 = await create_talent_partner(
        async_session, email="owner2@test.com"
    )
    sim1, tasks1 = await create_trial(async_session, created_by=talent_partner1)
    sim2, tasks2 = await create_trial(async_session, created_by=talent_partner2)

    cs1 = await create_candidate_session(async_session, trial=sim1)
    cs2 = await create_candidate_session(async_session, trial=sim2)

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
        headers={"x-dev-user-email": talent_partner1.email},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert {item["submissionId"] for item in items} == {sub1.id}
