from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.database.shared_database_models_model import Company, User
from app.shared.jobs import worker


@pytest_asyncio.fixture
async def authed_client(async_client, async_session, override_dependencies):
    company = Company(name="TestCo")
    async_session.add(company)
    await async_session.flush()
    talent_partner_user = User(
        name="TalentPartner One",
        email="talent_partner@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(talent_partner_user)
    await async_session.commit()
    await async_session.refresh(talent_partner_user)

    async def override_get_current_user():
        return talent_partner_user

    with override_dependencies({get_current_user: override_get_current_user}):
        yield async_client


async def run_one_job(async_session) -> None:
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
