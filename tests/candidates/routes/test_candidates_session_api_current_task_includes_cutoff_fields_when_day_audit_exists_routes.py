from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_includes_cutoff_fields_when_day_audit_exists(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-cutoff@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    day2_task = next(task for task in tasks if task.day_index == 2)
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    cutoff_at = datetime(2026, 3, 8, 17, 45, tzinfo=UTC)
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=day2_task.day_index,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="abc123def456",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["currentTask"]["dayIndex"] == 2
    assert body["currentTask"]["cutoffCommitSha"] == "abc123def456"
    assert body["currentTask"]["cutoffAt"] == "2026-03-08T17:45:00Z"
