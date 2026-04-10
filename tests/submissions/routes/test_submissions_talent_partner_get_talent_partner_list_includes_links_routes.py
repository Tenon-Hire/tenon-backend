from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_list_includes_links(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="links@test.com", name="TalentPartner Links"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        code_repo_path="org/repo",
        commit_sha="abc123",
        workflow_run_id="555",
        diff_summary_json=json.dumps({"base": "base1", "head": "head1"}),
        submitted_at=datetime.now(UTC),
    )
    resp = await async_client.get(
        "/api/submissions",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"items"}
    items = body["items"]
    found = next(i for i in items if i["submissionId"] == sub.id)
    assert found["repoFullName"] == "org/repo"
    assert found["workflowRunId"] == "555"
    assert found["commitSha"] == "abc123"
    assert found["workflowUrl"]
    assert found["commitUrl"]
    assert found["diffUrl"]
    assert "output" not in (found.get("testResults") or {})
    tr = found.get("testResults") or {}
    assert tr.get("artifactName") in (None, "winoe-test-results")
    assert tr.get("artifactPresent") in (None, True)
