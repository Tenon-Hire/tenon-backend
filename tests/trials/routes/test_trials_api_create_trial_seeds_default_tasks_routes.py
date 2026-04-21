from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_create_trial_seeds_default_tasks(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="owner1@example.com", name="Owner One"
    )

    payload = {
        "title": "Backend Node Trial",
        "role": "Backend Engineer",
        "seniority": "Mid",
        "preferredLanguageFramework": "Node.js, PostgreSQL",
    }

    res = await async_client.post(
        "/api/trials", json=payload, headers=auth_header_factory(talent_partner)
    )
    assert res.status_code == 201, res.text

    body = res.json()
    assert body["title"] == payload["title"]
    assert body["techStack"] == "Node.js, PostgreSQL"
    assert body["focus"] == ""
    assert body["companyContext"]["preferredLanguageFramework"] == "Node.js, PostgreSQL"
    assert len(body["tasks"]) == 5
    assert [t["day_index"] for t in body["tasks"]] == [1, 2, 3, 4, 5]
    assert body["tasks"][0]["type"] == "design"
    assert body["tasks"][4]["type"] == "reflection"
