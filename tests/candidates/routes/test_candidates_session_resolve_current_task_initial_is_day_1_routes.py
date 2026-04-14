from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_current_task_initial_is_day_1(async_client, async_session, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    talent_partner_email = "talent_partner1@winoe.com"
    await _seed_talent_partner(async_session, talent_partner_email)

    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": talent_partner_email},
    )
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        json={"confirm": True},
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert activate.status_code == 200, activate.text
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

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["candidateSessionId"] == cs_id
    assert body["isComplete"] is False
    assert body["currentDayIndex"] == 1
    assert body["currentTask"]["dayIndex"] == 1
    assert body["progress"]["completed"] == 0
    assert body["progress"]["total"] == 5
    assert body["currentTask"]["description"]
    assert body["currentWindow"] is not None
    assert body["currentWindow"]["windowStartAt"] is not None
    assert body["currentWindow"]["windowEndAt"] is not None
    assert isinstance(body["currentWindow"]["isOpen"], bool)
    assert body["currentWindow"]["now"] is not None
