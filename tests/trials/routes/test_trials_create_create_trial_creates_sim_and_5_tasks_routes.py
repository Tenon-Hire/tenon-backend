from __future__ import annotations

import pytest
from sqlalchemy import select

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
            "seniority": "Mid",
            "preferredLanguageFramework": "Node.js, PostgreSQL",
            "ai": {
                "noticeVersion": AI_NOTICE_DEFAULT_VERSION,
                "noticeText": AI_NOTICE_DEFAULT_TEXT,
                "evalEnabledByDay": {
                    "1": True,
                    "2": True,
                    "3": True,
                    "4": True,
                    "5": True,
                },
            },
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
            "code",
            "handoff",
            "reflection",
        ]
        assert [t["title"] for t in data["tasks"]] == [
            "Architecture Plan",
            "Feature Implementation",
            "Implementation Wrap-Up",
            "Demo Presentation",
            "Reflection Essay",
        ]
        assert data["techStack"] == "Node.js, PostgreSQL"
        assert data["focus"] == ""
        assert data["companyContext"]["preferredLanguageFramework"] == (
            "Node.js, PostgreSQL"
        )
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

        persisted_trial = (
            await async_session.execute(select(Trial).where(Trial.id == data["id"]))
        ).scalar_one()
        assert persisted_trial.day_window_overrides_enabled is True
        assert persisted_trial.day_window_overrides_json == {
            "5": {"startLocal": "09:00", "endLocal": "21:00"}
        }
        assert persisted_trial.day_window_start_local.strftime("%H:%M") == "09:00"
        assert persisted_trial.day_window_end_local.strftime("%H:%M") == "17:00"

        detail = await async_client.get(
            f"/api/trials/{data['id']}",
            headers={"Authorization": f"Bearer talent_partner:{user.email}"},
        )
        assert detail.status_code == 200, detail.text
        detail_body = detail.json()
        assert [task["type"] for task in detail_body["tasks"]] == [
            "design",
            "code",
            "code",
            "handoff",
            "reflection",
        ]
