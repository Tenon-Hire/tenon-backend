from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_create_trial_creates_sim_and_5_tasks(
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
        }

        resp = await async_client.post("/api/trials", json=payload)
        assert resp.status_code == 201, resp.text

        data = resp.json()
        assert "id" in data
        assert len(data["tasks"]) == 5
        assert [t["day_index"] for t in data["tasks"]] == [1, 2, 3, 4, 5]
        assert [t["type"] for t in data["tasks"]] == [
            "design",
            "code",
            "debug",
            "handoff",
            "documentation",
        ]
        assert data["templateKey"] == "python-fastapi"
        assert data["status"] == "generating"
        assert isinstance(data["scenarioGenerationJobId"], str)
        assert data["scenarioGenerationJobId"]
        assert data["ai"] == {
            "noticeVersion": AI_NOTICE_DEFAULT_VERSION,
            "noticeText": AI_NOTICE_DEFAULT_TEXT,
            "evalEnabledByDay": {
                "1": True,
                "2": True,
                "3": True,
                "4": True,
                "5": True,
            },
        }
