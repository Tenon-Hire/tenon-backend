from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *


@pytest.mark.asyncio
async def test_invite_duplicate_requests_idempotent(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    await seed_talent_partner(
        async_session,
        email="talent_partnerA@winoe.com",
        company_name="TalentPartner A Co",
    )

    sim_id = await _create_and_activate_trial(
        async_client, async_session, "talent_partnerA@winoe.com"
    )

    async def _invite():
        return await async_client.post(
            f"/api/trials/{sim_id}/invite",
            headers={"x-dev-user-email": "talent_partnerA@winoe.com"},
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
        )

    # async_client uses a shared session fixture, so true concurrency would
    # contend on a single transaction. Run sequentially as a best-effort check.
    first = await _invite()
    second = await _invite()
    assert first.status_code == 200
    assert second.status_code == 200
    outcomes = {first.json()["outcome"], second.json()["outcome"]}
    assert outcomes == {"created", "resent"}

    stmt = select(CandidateSession).where(CandidateSession.trial_id == sim_id)
    rows = (await async_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
