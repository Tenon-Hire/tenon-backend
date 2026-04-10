from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
async def test_current_task_advances_after_submission(
    async_client, async_session, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    talent_partner_email = "talent_partner1@winoe.com"
    await _seed_talent_partner(async_session, talent_partner_email)

    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=_next_local_window_start_utc(
            "America/New_York", days_ahead=-1
        ),
        candidate_timezone="America/New_York",
    )

    # Fetch Day 1 task
    day1_task = (
        await async_session.execute(
            select(Task).where(Task.trial_id == sim_id, Task.day_index == 1)
        )
    ).scalar_one()

    # Insert submission for Day 1
    submission = Submission(
        candidate_session_id=cs_id,
        task_id=day1_task.id,
        submitted_at=datetime.now(UTC),
        content_text="My design solution",
    )
    async_session.add(submission)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["currentDayIndex"] == 2
    assert body["progress"]["completed"] == 1
    assert body["currentTask"]["dayIndex"] == 2
