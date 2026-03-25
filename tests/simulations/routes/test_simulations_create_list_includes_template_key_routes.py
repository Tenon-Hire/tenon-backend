from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_create_api_utils import *


@pytest.mark.asyncio
async def test_list_includes_template_key(
    async_client, async_session, auth_header_factory
):
    company = Company(name="ListCo")
    async_session.add(company)
    await async_session.flush()

    user = User(
        name="Recruiter List",
        email="recruiter-list@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(user)
    await async_session.commit()

    create = await async_client.post(
        "/api/simulations",
        headers=auth_header_factory(user),
        json={
            "title": "ML Simulation",
            "role": "ML Infra Engineer",
            "techStack": "Python",
            "seniority": "Senior",
            "focus": "MLOps",
            "templateKey": "ml-infra-mlops",
        },
    )
    assert create.status_code == 201, create.text

    resp = await async_client.get("/api/simulations", headers=auth_header_factory(user))
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) >= 1
    item = next(i for i in items if i["id"] == create.json()["id"])
    assert item["templateKey"] == "ml-infra-mlops"
