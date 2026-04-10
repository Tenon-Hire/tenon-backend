from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_template_key_persists(
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
            "title": "Fullstack Trial",
            "role": "Fullstack Engineer",
            "techStack": "Next.js, FastAPI",
            "seniority": "Senior",
            "focus": "Ship a fullstack feature",
            "templateKey": "monorepo-nextjs-fastapi",
        }

        resp = await async_client.post("/api/trials", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["templateKey"] == "monorepo-nextjs-fastapi"

        sim_id = data["id"]
        from app.trials.repositories.trials_repositories_trials_trial_model import (
            Trial,
        )

        saved = await async_session.get(Trial, sim_id)
        assert saved is not None
        assert saved.template_key == "monorepo-nextjs-fastapi"
