from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_create_api_utils import *


@pytest.mark.asyncio
async def test_create_simulation_with_template_key_persists(
    async_client, async_session, override_dependencies
):
    company = Company(name="Acme Inc")
    async_session.add(company)
    await async_session.flush()

    user = User(
        name="Recruiter One",
        email="recruiter1@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()

    class FakeUser:
        id = user.id
        company_id = company.id
        role = "recruiter"

    with override_dependencies({get_current_user: lambda: FakeUser()}):
        payload = {
            "title": "Fullstack Simulation",
            "role": "Fullstack Engineer",
            "techStack": "Next.js, FastAPI",
            "seniority": "Senior",
            "focus": "Ship a fullstack feature",
            "templateKey": "monorepo-nextjs-fastapi",
        }

        resp = await async_client.post("/api/simulations", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["templateKey"] == "monorepo-nextjs-fastapi"

        sim_id = data["id"]
        from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
            Simulation,
        )

        saved = await async_session.get(Simulation, sim_id)
        assert saved is not None
        assert saved.template_key == "monorepo-nextjs-fastapi"
