from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_create_trial_with_invalid_template_key_returns_422(
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
            "templateKey": "unknown-template-key",
        }

        resp = await async_client.post("/api/trials", json=payload)
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["errorCode"] == "INVALID_TEMPLATE_KEY"
        detail_list = body["detail"]
        assert isinstance(detail_list, list)
        assert any(
            "Invalid templateKey" in str(item.get("msg")) for item in detail_list
        )
        assert "python-fastapi" in body.get("details", {}).get("allowed", [])
