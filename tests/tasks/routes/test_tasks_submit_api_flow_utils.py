from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Company, User


async def seed_talent_partner(
    session: AsyncSession, *, email: str, company_name: str
) -> User:
    company = Company(name=company_name)
    session.add(company)
    await session.flush()
    user = User(
        name=email.split("@")[0],
        email=email,
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def invite_candidate(
    async_client,
    sim_id: int,
    talent_partner_email: str,
    invite_email: str = "jane@example.com",
) -> dict:
    resp = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers={"x-dev-user-email": talent_partner_email},
        json={"candidateName": "Jane Doe", "inviteEmail": invite_email},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def claim_session(async_client, token: str, email: str) -> dict:
    resp = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": f"Bearer candidate:{email}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def get_current_task(async_client, cs_id: int, token: str) -> dict:
    resp = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


__all__ = [name for name in globals() if not name.startswith("__")]
