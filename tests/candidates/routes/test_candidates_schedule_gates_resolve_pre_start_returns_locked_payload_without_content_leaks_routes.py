from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_resolve_pre_start_returns_locked_payload_without_content_leaks(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="resolve-prestart@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="locked@example.com",
        with_default_schedule=False,
    )
    scheduled_start = _local_window_start_utc("America/New_York", days_ahead=2)
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=scheduled_start,
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.token}",
        headers={"Authorization": "Bearer candidate:locked@example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["candidateSessionId"] == candidate_session.id
    assert body["startAt"] == scheduled_start.isoformat().replace("+00:00", "Z")
    assert body["windowStartAt"] == scheduled_start.isoformat().replace("+00:00", "Z")
    assert body["windowEndAt"] is not None
    assert body["candidateTimezone"] == "America/New_York"
    assert body["trial"]["id"] == sim.id

    for key in (
        "storyline",
        "prestart",
        "currentTask",
        "tasks",
        "repoUrl",
        "codespaceUrl",
        "templateRepoFullName",
        "resources",
    ):
        assert key not in body

    payload_blob = json.dumps(body).lower()
    assert "github.com" not in payload_blob
    assert "codespace" not in payload_blob
