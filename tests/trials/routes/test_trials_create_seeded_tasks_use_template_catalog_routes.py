from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_seeded_tasks_use_template_catalog(
    async_client, async_session, override_dependencies
):
    company = Company(name="Acme Inc")
    async_session.add(company)
    await async_session.flush()

    user = User(
        name="TalentPartner One",
        email="talent_partner1@acme.com",
        role="talent_partner",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()

    class FakeUser:
        id = user.id
        company_id = company.id
        role = "talent_partner"

    with override_dependencies({get_current_user: lambda: FakeUser()}):
        payload = {
            "title": "Backend Node Trial",
            "role": "Backend Engineer",
            "techStack": "Node.js, PostgreSQL",
            "seniority": "Mid",
            "focus": "Build new API feature and debug an issue",
            "templateKey": "node-express-ts",
        }

        resp = await async_client.post("/api/trials", json=payload)
        assert resp.status_code == 201, resp.text
        sim_id = resp.json()["id"]

        rows = (
            await async_session.execute(
                select(Task).where(Task.trial_id == sim_id).order_by(Task.day_index)
            )
        ).scalars()
        tasks = list(rows)
        day2 = next(t for t in tasks if t.day_index == 2)
        day3 = next(t for t in tasks if t.day_index == 3)
        assert day2.template_repo == "winoe-hire-dev/winoe-template-node-express-ts"
        assert day3.template_repo == "winoe-hire-dev/winoe-template-node-express-ts"
