from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_can_fetch_known_submission(
    async_client, async_session: AsyncSession
):
    recruiter = await create_recruiter(
        async_session, email="recruiter1@test.com", name="Recruiter One"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = tasks[0]

    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        candidate_name="Jane Candidate",
        invite_email="a@b.com",
        status="in_progress",
    )

    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=task,
        content_text="my design answer",
        content_json={"kind": "day5_reflection", "sections": {"challenges": "x" * 20}},
        submitted_at=datetime.now(UTC),
        tests_passed=3,
        tests_failed=0,
        test_output="ok",
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["submissionId"] == sub.id
    assert data["candidateSessionId"] == cs.id
    assert data["task"]["taskId"] == task.id
    assert data["contentText"] == "my design answer"
    assert data["contentJson"] == {
        "kind": "day5_reflection",
        "sections": {"challenges": "x" * 20},
    }
    assert data["testResults"]["status"] == "passed"
    assert data["testResults"]["passed"] == 3
    assert data["testResults"]["failed"] == 0
