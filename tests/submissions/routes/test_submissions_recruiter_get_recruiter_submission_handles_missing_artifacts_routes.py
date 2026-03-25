from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_submission_handles_missing_artifacts(
    async_client, async_session: AsyncSession
):
    recruiter = await create_recruiter(async_session, email="nulls@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim, status="started")
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        submitted_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["workflowUrl"] is None
    assert payload["commitUrl"] is None
    assert payload["diffUrl"] is None
    assert payload["testResults"] is None
