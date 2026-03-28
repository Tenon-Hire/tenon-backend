from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_cannot_access_other_recruiters_submission(
    async_client, async_session: AsyncSession
):
    recruiter1 = await create_recruiter(
        async_session, email="recruiter1@test.com", name="Recruiter One"
    )
    recruiter2 = await create_recruiter(
        async_session, email="recruiter2@test.com", name="Recruiter Two"
    )

    sim, tasks = await create_simulation(async_session, created_by=recruiter2)
    task = tasks[0]

    cs = await create_candidate_session(
        async_session,
        simulation=sim,
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
        headers={"x-dev-user-email": recruiter1.email},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"] == "Submission access forbidden"
    combined = json.dumps(body)
    assert "Other Candidate" not in combined
