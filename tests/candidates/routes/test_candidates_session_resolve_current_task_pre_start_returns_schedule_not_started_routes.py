from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_current_task_pre_start_returns_schedule_not_started(
    async_client, async_session, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    talent_partner_email = "talent_partner-prestart@winoe.com"
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

    scheduled_start = _next_local_window_start_utc("America/New_York", days_ahead=2)
    await _apply_schedule(
        async_session,
        candidate_session_id=cs_id,
        scheduled_start_at=scheduled_start,
        candidate_timezone="America/New_York",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": "Bearer candidate:jane@example.com",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 409, res.text
    body = res.json()
    assert body["detail"] == "Trial has not started yet."
    assert body["errorCode"] == "SCHEDULE_NOT_STARTED"
    assert body["retryable"] is True
    assert body["details"]["startAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowStartAt"] == scheduled_start.isoformat().replace(
        "+00:00", "Z"
    )
    assert body["details"]["windowEndAt"] is not None
