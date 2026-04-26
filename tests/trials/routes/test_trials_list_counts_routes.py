import pytest
from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
    User,
)
from tests.shared.factories import create_trial
from tests.trials.routes.trials_list_api_utils import (
    run_one_job,
)


@pytest.mark.asyncio
async def test_list_trials_candidate_counts(authed_client, async_session):
    payload = {
        "title": "Sim With Candidates",
        "role": "Backend Engineer",
        "preferredLanguageFramework": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Counts",
    }
    r = await authed_client.post("/api/trials", json=payload)
    assert r.status_code == 201
    sim_id = r.json()["id"]
    await run_one_job(async_session)
    talent_partner = await async_session.scalar(
        select(User).where(User.email == "talent_partner@test.com")
    )
    assert talent_partner is not None
    sim = await async_session.get(Trial, sim_id)
    assert sim is not None and sim.active_scenario_version_id is not None
    other_trial, _ = await create_trial(
        async_session,
        created_by=talent_partner,
        title="Unrelated Trial",
    )

    cs1 = CandidateSession(
        trial_id=sim_id,
        scenario_version_id=sim.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate A",
        invite_email="a@example.com",
        token="tok_1",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    cs2 = CandidateSession(
        trial_id=sim_id,
        scenario_version_id=sim.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate B",
        invite_email="b@example.com",
        token="tok_2",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    other_cs1 = CandidateSession(
        trial_id=other_trial.id,
        scenario_version_id=other_trial.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate A",
        invite_email="other-a@example.com",
        token="tok_3",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    other_cs2 = CandidateSession(
        trial_id=other_trial.id,
        scenario_version_id=other_trial.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate B",
        invite_email="other-b@example.com",
        token="tok_4",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    other_cs3 = CandidateSession(
        trial_id=other_trial.id,
        scenario_version_id=other_trial.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate C",
        invite_email="other-c@example.com",
        token="tok_5",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    async_session.add_all([cs1, cs2, other_cs1, other_cs2, other_cs3])
    await async_session.commit()

    resp = await authed_client.get("/api/trials")
    assert resp.status_code == 200
    data = resp.json()
    item = next(x for x in data if x["id"] == sim_id)
    assert item["numCandidates"] == 2
    other_item = next(x for x in data if x["id"] == other_trial.id)
    assert other_item["numCandidates"] == 3
