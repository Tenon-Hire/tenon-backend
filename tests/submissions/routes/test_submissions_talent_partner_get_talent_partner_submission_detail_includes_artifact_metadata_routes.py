from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_submission_detail_includes_artifact_metadata(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(async_session, email="detail@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="started")

    long_stdout = "x" * 21000
    output = {
        "status": "failed",
        "passed": 2,
        "failed": 1,
        "total": 3,
        "stdout": long_stdout,
        "stderr": "short error",
        "runId": 777,
        "conclusion": "failure",
        "summary": {"note": "check"},
    }
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        code_repo_path="acme/repo1",
        commit_sha="deadbeef",
        workflow_run_id="42",
        diff_summary_json=json.dumps({"base": "base-branch", "head": "feature"}),
        test_output=json.dumps(output),
        last_run_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["workflowUrl"].endswith("/actions/runs/42")
    assert body["commitUrl"].endswith("/commit/deadbeef")
    assert body["diffUrl"].endswith("/compare/base-branch...feature")
    assert body["code"]["repoFullName"] == "acme/repo1"

    test_results = body["testResults"]
    assert test_results["status"] == "failed"
    assert test_results["total"] == 3
    assert test_results["runId"] == 777
    assert test_results["workflowRunId"] == "42"
    assert test_results["conclusion"] == "failure"
    assert test_results["summary"] == {"note": "check"}
    assert test_results["runStatus"] is None
    assert test_results["artifactName"] == "winoe-test-results"
    assert test_results["artifactPresent"] is True
    assert test_results["stdout"].endswith("(truncated)")
    assert test_results["stdoutTruncated"] is True
    assert len(test_results["stdout"]) < len(long_stdout)
    assert test_results["output"]["stdout"].endswith("(truncated)")
    assert test_results["stderr"] == "short error"
    assert test_results["stderrTruncated"] is False
