from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_default_template_key_applied(
    async_client, async_session, auth_header_factory
):
    company = Company(name="DefaultCo")
    async_session.add(company)
    await async_session.flush()

    user = User(
        name="TalentPartner Default",
        email="talent_partner-default@acme.com",
        role="talent_partner",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()

    resp = await async_client.post(
        "/api/trials",
        headers=auth_header_factory(user),
        json={
            "title": "Backend Node Trial",
            "role": "Backend Engineer",
            "techStack": "Node.js, PostgreSQL",
            "seniority": "Mid",
            "focus": "Build new API feature and debug an issue",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["templateKey"] == "python-fastapi"
    sim_id = data["id"]

    rows = (
        await async_session.execute(
            select(Task).where(Task.trial_id == sim_id).order_by(Task.day_index)
        )
    ).scalars()
    tasks = list(rows)
    day2 = next(t for t in tasks if t.day_index == 2)
    day3 = next(t for t in tasks if t.day_index == 3)
    assert day2.template_repo == "winoe-hire-dev/winoe-template-python-fastapi"
    assert day3.template_repo == "winoe-hire-dev/winoe-template-python-fastapi"
