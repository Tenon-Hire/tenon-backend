from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as cs_repo,
)
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_rejects_after_day_audit_exists(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="run-cutoff@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=tasks[1].day_index,
        cutoff_at=datetime(2026, 3, 8, 18, 15, tzinfo=UTC),
        cutoff_commit_sha="cutoff-day2-run-sha",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=candidate_header_factory(cs),
        json={},
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["details"]["cutoffCommitSha"] == "cutoff-day2-run-sha"
    assert body["details"]["evalBasisRef"] == "refs/heads/main@cutoff"
