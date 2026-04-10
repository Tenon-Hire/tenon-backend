from __future__ import annotations

from types import SimpleNamespace

from app.shared.database.shared_database_models_model import Company, User


async def create_user(
    async_session,
    *,
    company_name: str | None,
    name: str,
    email: str,
    role: str = "talent_partner",
    company_id: int | None = None,
):
    if company_id is None:
        company = Company(name=company_name or "TestCo")
        async_session.add(company)
        await async_session.flush()
    else:
        company = SimpleNamespace(id=company_id, name=company_name or "")

    user = User(
        name=name,
        email=email,
        role=role,
        company_id=company.id,  # type: ignore[arg-type]
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()
    return user, company


async def create_trial(
    async_client, auth_header_factory, talent_partner, json_payload: dict
) -> int:
    create_res = await async_client.post(
        "/api/trials",
        headers=auth_header_factory(talent_partner),
        json=json_payload,
    )
    assert create_res.status_code == 201, create_res.text
    return create_res.json()["id"]
