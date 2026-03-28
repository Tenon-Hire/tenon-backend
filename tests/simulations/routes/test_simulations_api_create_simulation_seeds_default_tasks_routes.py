from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_api_utils import *


@pytest.mark.asyncio
async def test_create_simulation_seeds_default_tasks(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="owner1@example.com", name="Owner One"
    )

    payload = {
        "title": "Backend Node Simulation",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Build a new API and iterate over 5 days",
    }

    res = await async_client.post(
        "/api/simulations", json=payload, headers=auth_header_factory(recruiter)
    )
    assert res.status_code == 201, res.text

    body = res.json()
    assert body["title"] == payload["title"]
    assert len(body["tasks"]) == 5
    assert [t["day_index"] for t in body["tasks"]] == [1, 2, 3, 4, 5]
    assert body["tasks"][0]["type"] == "design"
