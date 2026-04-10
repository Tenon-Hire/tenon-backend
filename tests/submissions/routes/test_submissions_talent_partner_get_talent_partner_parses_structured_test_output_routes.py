from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_parses_structured_test_output(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="struct@test.com", name="Struct TalentPartner"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = tasks[1]
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")

    output = {
        "status": "failed",
        "passed": 1,
        "failed": 2,
        "total": 3,
        "stdout": "prints",
        "stderr": "boom",
        "timeout": False,
    }
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=task,
        content_text=None,
        tests_passed=None,
        tests_failed=None,
        test_output=json.dumps(output),
        last_run_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["testResults"]
    assert data["status"] == "failed"
    assert data["passed"] == 1
    assert data["failed"] == 2
    assert data["total"] == 3
    assert data["output"]["stdout"] == "prints"
    assert data["output"]["stderr"] == "boom"
    assert data["output"].get("summary") is None
    assert data["artifactName"] == "winoe-test-results"
    assert data["artifactPresent"] is True
