from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_invite_resends_existing_active(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    await seed_talent_partner(
        async_session,
        email="talent_partnerA@winoe.com",
        company_name="TalentPartner A Co",
    )

    sim_id = await _create_and_generate_trial(
        async_client, async_session, "talent_partnerA@winoe.com"
    )

    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert first.status_code == 200
    first_body = first.json()

    second = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["candidateSessionId"] == first_body["candidateSessionId"]
    assert second_body["outcome"] == "resent"

    stmt = select(CandidateSession).where(CandidateSession.trial_id == sim_id)
    rows = (await async_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
