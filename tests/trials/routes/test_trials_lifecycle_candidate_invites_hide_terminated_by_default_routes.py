from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_candidate_invites_hide_terminated_by_default(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="candidate-filter@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="candidate-filter@example.com",
    )
    await async_session.commit()

    terminated = await async_client.post(
        f"/api/trials/{trial.id}/terminate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert terminated.status_code == 200, terminated.text

    default_invites = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert default_invites.status_code == 200, default_invites.text
    assert default_invites.json() == []

    include_terminated = await async_client.get(
        "/api/candidate/invites?includeTerminated=true",
        headers={"Authorization": "Bearer candidate:candidate-filter@example.com"},
    )
    assert include_terminated.status_code == 200, include_terminated.text
    rows = include_terminated.json()
    assert len(rows) == 1
    assert rows[0]["candidateSessionId"] == candidate_session.id
