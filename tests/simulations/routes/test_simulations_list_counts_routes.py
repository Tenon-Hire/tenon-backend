import pytest

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
)
from tests.simulations.routes.simulations_list_api_utils import (
    run_one_job,
)


@pytest.mark.asyncio
async def test_list_simulations_candidate_counts(authed_client, async_session):
    payload = {
        "title": "Sim With Candidates",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Counts",
    }
    r = await authed_client.post("/api/simulations", json=payload)
    assert r.status_code == 201
    sim_id = r.json()["id"]
    await run_one_job(async_session)
    sim = await async_session.get(Simulation, sim_id)
    assert sim is not None and sim.active_scenario_version_id is not None

    cs1 = CandidateSession(
        simulation_id=sim_id,
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
        simulation_id=sim_id,
        scenario_version_id=sim.active_scenario_version_id,
        candidate_user_id=None,
        candidate_name="Candidate B",
        invite_email="b@example.com",
        token="tok_2",
        status="invited",
        started_at=None,
        completed_at=None,
    )
    async_session.add_all([cs1, cs2])
    await async_session.commit()

    resp = await authed_client.get("/api/simulations")
    assert resp.status_code == 200
    data = resp.json()
    item = next(x for x in data if x["id"] == sim_id)
    assert item["numCandidates"] == 2
