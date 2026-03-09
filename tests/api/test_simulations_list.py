from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.auth.current_user import get_current_user
from app.domains import CandidateSession, Company, Simulation, User
from app.jobs import worker


@pytest_asyncio.fixture
async def recruiter_user(async_session):
    company = Company(name="TestCo")
    async_session.add(company)
    await async_session.flush()  # company.id

    user = User(
        name="Recruiter One",
        email="recruiter@test.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def authed_client(async_client, recruiter_user, override_dependencies):
    async def override_get_current_user():
        return recruiter_user

    with override_dependencies({get_current_user: override_get_current_user}):
        yield async_client


async def _run_one_job(async_session) -> None:
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="sim-list-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True


@pytest.mark.asyncio
async def test_list_simulations_empty(authed_client):
    resp = await authed_client.get("/api/simulations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_simulations_returns_two(authed_client):
    payload1 = {
        "title": "Sim A",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "A",
    }
    payload2 = {
        "title": "Sim B",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "B",
    }

    r1 = await authed_client.post("/api/simulations", json=payload1)
    r2 = await authed_client.post("/api/simulations", json=payload2)
    assert r1.status_code == 201
    assert r2.status_code == 201

    resp = await authed_client.get("/api/simulations")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    titles = {x["title"] for x in data}
    assert titles == {"Sim A", "Sim B"}

    for item in data:
        assert "id" in item
        assert item["role"] == "Backend Engineer"
        assert item["techStack"] == "Node.js, PostgreSQL"
        assert "createdAt" in item
        assert item["numCandidates"] == 0


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
    await _run_one_job(async_session)
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


@pytest.mark.asyncio
async def test_list_simulations_includes_seniority_and_ai_eval_summary(authed_client):
    payload = {
        "title": "Sim With AI Settings",
        "role": "Frontend Engineer",
        "techStack": "react-nextjs",
        "seniority": "mid",
        "focus": "Prioritize API ergonomics.",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "evalEnabledByDay": {
                "1": True,
                "2": True,
                "3": False,
                "4": False,
                "5": True,
            },
        },
    }
    create_res = await authed_client.post("/api/simulations", json=payload)
    assert create_res.status_code == 201, create_res.text
    sim_id = create_res.json()["id"]

    list_res = await authed_client.get("/api/simulations")
    assert list_res.status_code == 200, list_res.text
    item = next(x for x in list_res.json() if x["id"] == sim_id)
    assert item["seniority"] == "mid"
    assert item["companyContext"] == payload["companyContext"]
    assert item["ai"]["noticeVersion"] == "mvp1"
    assert item["ai"]["evalEnabledByDay"] == payload["ai"]["evalEnabledByDay"]


@pytest.mark.asyncio
async def test_list_simulations_does_not_show_other_users(authed_client, async_session):
    other_company = Company(name="OtherCo")
    async_session.add(other_company)
    await async_session.flush()

    other_user = User(
        name="Recruiter Two",
        email="other@test.com",
        role="recruiter",
        company_id=other_company.id,
        password_hash=None,
    )
    async_session.add(other_user)
    await async_session.flush()

    # Create simulation for other user (direct insert)
    from app.domains.simulations.simulation import Simulation

    other_sim = Simulation(
        title="Other User Sim",
        role="Backend Engineer",
        tech_stack="Node.js, PostgreSQL",
        seniority="Mid",
        focus="Should not appear",
        scenario_template="default-5day-node-postgres",
        company_id=other_company.id,
        created_by=other_user.id,
    )
    async_session.add(other_sim)
    await async_session.commit()

    resp = await authed_client.get("/api/simulations")
    assert resp.status_code == 200
    titles = {x["title"] for x in resp.json()}
    assert "Other User Sim" not in titles


@pytest.mark.asyncio
async def test_list_simulations_forbidden_for_non_recruiter(
    async_client, async_session, override_dependencies
):
    company = Company(name="CandidateCo")
    async_session.add(company)
    await async_session.flush()

    candidate_user = User(
        name="Candidate User",
        email="candidate@test.com",
        role="candidate",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(candidate_user)
    await async_session.commit()

    def override_user():
        return candidate_user

    with override_dependencies({get_current_user: override_user}):
        resp = await async_client.get("/api/simulations")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Recruiter access required"
