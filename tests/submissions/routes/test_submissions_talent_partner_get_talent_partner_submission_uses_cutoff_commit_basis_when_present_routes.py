from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_talent_partner_get_api_utils import *


@pytest.mark.asyncio
async def test_talent_partner_submission_uses_cutoff_commit_basis_when_present(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="cutoff-evidence@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    day2_task = next(task for task in tasks if task.day_index == 2)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    submitted_at = datetime.now(UTC).replace(microsecond=0)
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=day2_task,
        code_repo_path="org/candidate-repo",
        commit_sha="mutable-sha",
        workflow_run_id="5150",
        tests_passed=1,
        tests_failed=0,
        last_run_at=submitted_at,
        submitted_at=submitted_at,
    )
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    day_audit, created = await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="cutoff-sha",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert created is True
    assert day_audit.cutoff_commit_sha == "cutoff-sha"

    list_resp = await async_client.get(
        "/api/submissions",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert list_resp.status_code == 200, list_resp.text
    list_item = next(
        item for item in list_resp.json()["items"] if item["submissionId"] == sub.id
    )
    assert list_item["commitSha"] == "cutoff-sha"
    assert list_item["cutoffCommitSha"] == "cutoff-sha"
    assert list_item["cutoffAt"] == "2026-03-10T21:00:00Z"
    assert list_item["evalBasisRef"] == "refs/heads/main@cutoff"
    assert list_item["commitUrl"].endswith("/commit/cutoff-sha")

    detail_resp = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["commitSha"] == "cutoff-sha"
    assert detail["cutoffCommitSha"] == "cutoff-sha"
    assert detail["cutoffAt"] == "2026-03-10T21:00:00Z"
    assert detail["evalBasisRef"] == "refs/heads/main@cutoff"
    assert detail["commitUrl"].endswith("/commit/cutoff-sha")
    assert detail["testResults"]["commitSha"] == "cutoff-sha"
