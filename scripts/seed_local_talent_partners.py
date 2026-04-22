import argparse
import asyncio

from sqlalchemy import select, text

from app.shared.auth.dependencies.shared_auth_dependencies_local_talent_partner_company_utils import (
    ensure_local_talent_partner_company,
)
from app.shared.database import async_session_maker, engine
from app.shared.database.shared_database_models_model import Base
from app.talent_partners.repositories.users.talent_partners_repositories_users_talent_partners_users_core_model import (
    User,
)


async def _reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        table_names = [
            table.name
            for table in Base.metadata.sorted_tables
            if table.name != "alembic_version"
        ]
        if not table_names:
            return
        if conn.dialect.name == "sqlite":
            await conn.exec_driver_sql("PRAGMA foreign_keys = OFF")
            try:
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())
            finally:
                await conn.exec_driver_sql("PRAGMA foreign_keys = ON")
            return
        quoted = ", ".join(f'"{name}"' for name in table_names)
        await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


async def main(*, reset: bool = False):
    """Seed default talent_partners for local development."""
    if reset:
        await _reset_database()
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as s:
        c = await ensure_local_talent_partner_company(s)

        talent_partners = [
            ("Local TalentPartner 1", "talent_partner1@local.test"),
            ("Local TalentPartner 2", "talent_partner2@local.test"),
        ]
        verification_talent_partner = (
            "talentPartner",
            "robel.kebede@bison.howard.edu",
        )

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

        verification_name, verification_email = verification_talent_partner
        verification_user = await s.scalar(
            select(User).where(User.email == verification_email)
        )
        if not verification_user:
            verification_user = User(
                name=verification_name,
                email=verification_email,
                role="talent_partner",
                company_id=c.id,
                password_hash=None,
            )
            s.add(verification_user)
            created.append(verification_email)
        else:
            if verification_user.name != verification_name:
                verification_user.name = verification_name
                repaired.append(verification_email)
            if verification_user.role != "talent_partner":
                verification_user.role = "talent_partner"
                repaired.append(verification_email)
            if verification_user.company_id != c.id:
                verification_user.company_id = c.id
                repaired.append(verification_email)

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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete local application rows before seeding while preserving schema.",
    )
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
