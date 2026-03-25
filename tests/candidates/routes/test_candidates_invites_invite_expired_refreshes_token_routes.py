from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *


@pytest.mark.asyncio
async def test_invite_expired_refreshes_token(
    async_client, async_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")

    await seed_recruiter(
        async_session,
        email="recruiterA@tenon.com",
        company_name="Recruiter A Co",
    )

    sim_id = await _create_and_activate_simulation(
        async_client, async_session, "recruiterA@tenon.com"
    )

    first = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers={"x-dev-user-email": "recruiterA@tenon.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert first.status_code == 200
    first_body = first.json()

    stmt = select(CandidateSession).where(
        CandidateSession.id == first_body["candidateSessionId"]
    )
    cs = (await async_session.execute(stmt)).scalar_one()
    cs.expires_at = datetime.now(UTC) - timedelta(days=1)
    await async_session.commit()

    second = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers={"x-dev-user-email": "recruiterA@tenon.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["candidateSessionId"] == first_body["candidateSessionId"]
    assert second_body["token"] != first_body["token"]
    assert second_body["outcome"] == "created"
