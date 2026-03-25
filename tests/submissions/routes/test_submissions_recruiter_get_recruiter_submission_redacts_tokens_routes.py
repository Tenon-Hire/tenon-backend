from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_submission_redacts_tokens(
    async_client, async_session: AsyncSession
):
    recruiter = await create_recruiter(async_session, email="redact@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim, status="started")
    output = {
        "status": "failed",
        "passed": 0,
        "failed": 1,
        "total": 1,
        "stdout": "fail ghp_1234567890abcdef",
        "stderr": "Authorization: Bearer SECRET",
    }
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        code_repo_path="acme/repo3",
        workflow_run_id="789",
        diff_summary_json=json.dumps({"base": "a", "head": "b"}),
        test_output=json.dumps(output),
        last_run_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["testResults"]
    combined = json.dumps(body)
    assert "ghp_1234567890abcdef" not in combined
    assert "Authorization: Bearer SECRET" not in combined
    assert "[redacted]" in combined
