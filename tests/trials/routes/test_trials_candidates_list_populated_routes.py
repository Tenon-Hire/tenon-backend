from datetime import UTC, datetime

import pytest

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    WinoeReport,
)
from tests.trials.routes.trials_candidates_api_utils import (
    attach_active_scenario,
    create_trial,
    seed_talent_partner,
)


@pytest.mark.asyncio
async def test_trial_with_multiple_sessions_returns_all_and_has_report(
    async_client, async_session
):
    user, company = await seed_talent_partner(
        async_session,
        email="r2@acme.com",
        company_name="Acme2",
        name="TalentPartner Two",
    )
    sim = await create_trial(
        async_session,
        user_id=user.id,
        company_id=company.id,
        title="Sim With Candidates",
    )
    scenario = await attach_active_scenario(async_session, sim)

    cs1 = CandidateSession(
        trial_id=sim.id,
        scenario_version_id=scenario.id,
        candidate_name="Ada Lovelace",
        invite_email="ada@example.com",
        token="tok-1",
        status="not_started",
        expires_at=None,
    )
    cs2 = CandidateSession(
        trial_id=sim.id,
        scenario_version_id=scenario.id,
        candidate_name="Bob",
        invite_email="bob@example.com",
        token="tok-2",
        status="completed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        expires_at=None,
    )
    async_session.add_all([cs1, cs2])
    await async_session.flush()
    async_session.add(
        WinoeReport(candidate_session_id=cs2.id, generated_at=datetime.now(UTC))
    )
    await async_session.commit()

    resp = await async_client.get(
        f"/api/trials/{sim.id}/candidates",
        headers={"x-dev-user-email": user.email},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    by_id = {row["candidateSessionId"]: row for row in data}
    assert by_id[cs1.id]["inviteEmail"] == "ada@example.com"
    assert by_id[cs1.id]["candidateName"] == "Ada Lovelace"
    assert by_id[cs1.id]["status"] == "not_started"
    assert by_id[cs1.id]["hasWinoeReport"] is False
    assert by_id[cs2.id]["inviteEmail"] == "bob@example.com"
    assert by_id[cs2.id]["candidateName"] == "Bob"
    assert by_id[cs2.id]["status"] == "completed"
    assert by_id[cs2.id]["hasWinoeReport"] is True
