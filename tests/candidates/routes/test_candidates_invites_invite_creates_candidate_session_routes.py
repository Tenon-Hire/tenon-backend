from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_invite_creates_candidate_session(
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

    # Invite candidate
    resp = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body["candidateSessionId"], int)
    assert body["candidateSessionId"] > 0

    assert isinstance(body["token"], str)
    # token_urlsafe(32) is typically ~43 chars, but just ensure "unguessable-ish"
    assert len(body["token"]) >= 32

    assert isinstance(body["inviteUrl"], str)
    assert body["inviteUrl"].endswith(f"/candidate/session/{body['token']}")
    assert body["outcome"] == "created"

    # Verify DB row
    stmt = select(CandidateSession).where(
        CandidateSession.id == body["candidateSessionId"]
    )
    cs = (await async_session.execute(stmt)).scalar_one()

    assert cs.trial_id == sim_id
    assert cs.invite_email == "jane@example.com"
    assert cs.status == "not_started"
    assert cs.token == body["token"]

    # candidateName -> candidate_name
    assert cs.candidate_name == "Jane Doe"
