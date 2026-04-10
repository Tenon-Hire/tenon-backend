from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_cannot_access_other_talent_partners_submission(
    async_client, async_session: AsyncSession
):
    talent_partner1 = await create_talent_partner(
        async_session, email="talent_partner1@test.com", name="TalentPartner One"
    )
    talent_partner2 = await create_talent_partner(
        async_session, email="talent_partner2@test.com", name="TalentPartner Two"
    )

    sim, tasks = await create_trial(async_session, created_by=talent_partner2)
    task = tasks[0]

    cs = await create_candidate_session(
        async_session,
        trial=sim,
        candidate_name="Other Candidate",
        invite_email="x@y.com",
        status="in_progress",
    )

    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=task,
        submitted_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner1.email},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"] == "Submission access forbidden"
    combined = json.dumps(body)
    assert "Other Candidate" not in combined
