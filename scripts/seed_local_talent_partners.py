import asyncio

from sqlalchemy import select

from app.shared.auth.dependencies.shared_auth_dependencies_local_talent_partner_company_utils import (
    ensure_local_talent_partner_company,
)
from app.shared.database import async_session_maker, engine
from app.shared.database.shared_database_models_model import Base
from app.talent_partners.repositories.users.talent_partners_repositories_users_talent_partners_users_core_model import (
    User,
)


async def main():
    """Seed default talent_partners for local development."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as s:
        c = await ensure_local_talent_partner_company(s)

        talent_partners = [
            ("Local TalentPartner 1", "talent_partner1@local.test"),
            ("Local TalentPartner 2", "talent_partner2@local.test"),
        ]

        created = []
        repaired = []
        for name, email in talent_partners:
            u = await s.scalar(select(User).where(User.email == email))
            if not u:
                u = User(
                    name=name,
                    email=email,
                    role="talent_partner",
                    company_id=c.id,
                    password_hash=None,
                )
                s.add(u)
                created.append(email)

        existing_talent_partners = (
            await s.execute(
                select(User).where(
                    User.role == "talent_partner",
                    User.company_id.is_(None),
                )
            )
        ).scalars()
        for talent_partner in existing_talent_partners:
            talent_partner.company_id = c.id
            repaired.append(talent_partner.email)

        await s.commit()

        messages = []
        if created:
            messages.append(f"seeded: {', '.join(created)}")
        if repaired:
            messages.append(f"repaired company_id: {', '.join(repaired)}")
        if messages:
            print("TalentPartners ready (" + "; ".join(messages) + ").")
        else:
            print("TalentPartners already exist (no changes).")


if __name__ == "__main__":
    asyncio.run(main())
