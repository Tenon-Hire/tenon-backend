from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_code_task_persists_actions_results(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    talent_partner = await create_talent_partner(
        async_session, email="code-submit@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    # Seed day 1 submission to unlock day 2 code task
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    actions_stubber(
        result=ActionsRunResult(
            status="failed",
            run_id=555,
            conclusion="failure",
            passed=1,
            failed=2,
            total=3,
            stdout="prints",
            stderr="boom",
            head_sha="abc123",
            html_url="https://example.com/run/555",
            raw=None,
        )
    )

    headers = candidate_header_factory(cs)
    await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )
    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=headers,
        json={},
    )

    assert resp.status_code == 201, resp.text
    sub = await async_session.get(Submission, resp.json()["submissionId"])
    assert sub.tests_passed == 1
    assert sub.tests_failed == 2
    assert sub.last_run_at is not None
    assert sub.test_output
    payload = json.loads(sub.test_output)
    assert payload["status"] == "failed"
    assert payload["passed"] == 1
    assert payload["failed"] == 2
    assert payload["total"] == 3
    assert payload["stdout"] == "prints"
    assert payload["stderr"] == "boom"
    assert sub.commit_sha == "abc123"
    assert sub.workflow_run_id == "555"
    diff_summary = json.loads(sub.diff_summary_json or "{}")
    assert diff_summary["base"] == "base-sha-123"
    assert diff_summary["head"] == "abc123"
    assert "files" in diff_summary

    detail = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["diffSummary"] == diff_summary
    assert detail_body["diffUrl"].endswith("base-sha-123...abc123")
