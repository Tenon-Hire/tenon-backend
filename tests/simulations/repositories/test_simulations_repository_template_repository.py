import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Simulation
from app.submissions.repositories import (
    submissions_repositories_submissions_core_repository as submissions_repo,
)
from tests.shared.factories import create_company


@pytest.mark.asyncio
async def test_simulation_template_returns_scenario(async_session: AsyncSession):
    company = await create_company(async_session, name="Acme")
    sim = Simulation(
        company_id=company.id,
        title="Sim",
        role="Backend",
        tech_stack="Node",
        seniority="Mid",
        focus="Focus string",
        scenario_template="scenario-key",
        created_by=0,
        status="generating",
    )
    async_session.add(sim)
    await async_session.commit()

    result = await submissions_repo.simulation_template(async_session, sim.id)
    assert result == "scenario-key"


@pytest.mark.asyncio
async def test_simulation_template_falls_back_to_focus(async_session: AsyncSession):
    company = await create_company(async_session, name="Fallback Co")
    sim = Simulation(
        company_id=company.id,
        title="Sim",
        role="Backend",
        tech_stack="Node",
        seniority="Mid",
        focus="Focus string",
        scenario_template="",
        created_by=0,
        status="generating",
    )
    async_session.add(sim)
    await async_session.commit()

    result = await submissions_repo.simulation_template(async_session, sim.id)
    assert result == "Focus string"


@pytest.mark.asyncio
async def test_simulation_template_returns_none_for_missing(
    async_session: AsyncSession,
):
    result = await submissions_repo.simulation_template(
        async_session, simulation_id=9999
    )
    assert result is None
