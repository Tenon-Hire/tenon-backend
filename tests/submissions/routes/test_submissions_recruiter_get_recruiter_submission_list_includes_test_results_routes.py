from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_recruiter_get_api_utils import *


@pytest.mark.asyncio
async def test_recruiter_submission_list_includes_test_results(
    async_client, async_session: AsyncSession
):
    recruiter = await create_recruiter(async_session, email="listmeta@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim, status="started")

    output = {
        "status": "passed",
        "passed": 4,
        "failed": 0,
        "total": 4,
        "stdout": "great",
        "stderr": "",
        "runId": 991,
        "conclusion": "success",
    }
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        code_repo_path="acme/repo2",
        commit_sha="cafebabe",
        workflow_run_id="321",
        diff_summary_json=json.dumps({"base": "main", "head": "feature2"}),
        test_output=json.dumps(output),
        last_run_at=datetime.now(UTC),
    )

    resp = await async_client.get(
        "/api/submissions",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json()["items"] if i["submissionId"] == sub.id)
    test_results = item["testResults"]
    assert test_results["status"] == "passed"
    assert test_results["passed"] == 4
    assert test_results["failed"] == 0
    assert test_results["total"] == 4
    assert test_results["runStatus"] is None
    assert test_results["workflowUrl"].endswith("/actions/runs/321")
    assert test_results["commitUrl"].endswith("/commit/cafebabe")
    assert item["diffUrl"].endswith("/compare/main...feature2")
    assert "output" not in test_results or test_results["output"] is None
    assert test_results["stdoutTruncated"] is False
    assert test_results["stderrTruncated"] is False
    assert test_results["artifactName"] == "tenon-test-results"
    assert test_results["artifactPresent"] is True
