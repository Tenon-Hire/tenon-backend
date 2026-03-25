from __future__ import annotations

from app.shared.database.shared_database_models_model import (
    Company,
    ScenarioVersion,
    Simulation,
    User,
)


async def seed_recruiter(async_session, *, email: str, company_name: str, name: str):
    company = Company(name=company_name)
    async_session.add(company)
    await async_session.flush()
    user = User(
        name=name,
        email=email,
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()
    return user, company


async def create_simulation(
    async_session, *, user_id: int, company_id: int, title: str
):
    sim = Simulation(
        title=title,
        role="Backend Engineer",
        tech_stack="Node.js + Postgres",
        seniority="Mid",
        focus="",
        scenario_template="default-5day-node-postgres",
        company_id=company_id,
        created_by=user_id,
    )
    async_session.add(sim)
    await async_session.flush()
    return sim


async def attach_active_scenario(async_session, sim: Simulation):
    scenario = ScenarioVersion(
        simulation_id=sim.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {sim.title}",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="",
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )
    async_session.add(scenario)
    await async_session.flush()
    sim.active_scenario_version_id = scenario.id
    await async_session.flush()
    return scenario
