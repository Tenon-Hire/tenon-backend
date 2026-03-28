from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_create_api_utils import *


@pytest.mark.asyncio
async def test_create_simulation_forbidden_for_non_recruiter(
    async_client, async_session, override_dependencies
):
    company = Company(name="Acme Inc")
    async_session.add(company)
    await async_session.flush()

    user = User(
        name="Candidate User",
        email="candidate@acme.com",
        role="candidate",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    class FakeCandidate:
        id = user.id
        company_id = company.id
        role = "candidate"

    with override_dependencies({get_current_user: lambda: FakeCandidate()}):
        payload = {
            "title": "Backend Node Simulation",
            "role": "Backend Engineer",
            "techStack": "Node.js, PostgreSQL",
            "seniority": "Mid",
            "focus": "Build new API feature and debug an issue",
        }

        resp = await async_client.post("/api/simulations", json=payload)
        assert resp.status_code == 403, resp.text
