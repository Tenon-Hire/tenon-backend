from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_submission_handles_missing_artifacts(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(async_session, email="nulls@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="started")
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        submitted_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["workflowUrl"] is None
    assert payload["commitUrl"] is None
    assert payload["diffUrl"] is None
    assert payload["testResults"] is None
