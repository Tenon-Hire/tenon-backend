from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Company, User

from .shared_factories_company_utils import create_company


async def create_talent_partner(
    session: AsyncSession,
    *,
    email: str = "talent_partner@example.com",
    company: Company | None = None,
    company_name: str | None = None,
    name: str | None = None,
) -> User:
    company = company or await create_company(
        session, name=company_name or f"{email}-co"
    )
    user = User(
        name=name or email.split("@")[0],
        email=email,
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    session.add(user)
    await session.flush()
    return user
