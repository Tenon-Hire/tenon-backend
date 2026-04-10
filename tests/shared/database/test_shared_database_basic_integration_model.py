import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Company, Trial, User


@pytest.mark.asyncio
async def test_create_trial(async_session: AsyncSession):
    # 1. Create company
    company = Company(name="TestCo")
    async_session.add(company)
    await async_session.flush()

    # 2. Create user (creator of the trial)
    user = User(
        name="Admin User",
        email="admin@test.com",
        role="admin",
        company_id=company.id,
        password_hash="hashedpw",
    )
    async_session.add(user)
    await async_session.flush()

    # 3. Create trial referencing both
    sim = Trial(
        company_id=company.id,
        title="Backend Hiring Trial",
        role="Backend Engineer",
        tech_stack="Node.js, Postgres",
        seniority="mid",
        scenario_template="backend_v1",
        created_by=user.id,
        status="generating",
    )

    async_session.add(sim)
    await async_session.commit()
    await async_session.refresh(sim)

    assert sim.id is not None
    assert sim.created_by == user.id
