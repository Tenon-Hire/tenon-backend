from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.shared.auth import auth0
from app.shared.auth import shared_auth_current_user_utils as current_user
from app.shared.database import get_session


@pytest.mark.asyncio
async def test_create_trial_returns_409_for_talent_partner_without_company(
    async_session, monkeypatch, override_dependencies
):
    def fake_decode_auth0_token(_token: str) -> dict[str, str]:
        return {
            "email": "unonboarded@example.com",
            "name": "Incomplete TalentPartner",
            "sub": "auth0|unonboarded",
            "permissions": ["talent_partner:access"],
        }

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )

    async def override_get_session():
        yield async_session

    monkeypatch.setattr(auth0, "decode_auth0_token", fake_decode_auth0_token)
    monkeypatch.setattr(current_user, "async_session_maker", session_maker)
    with override_dependencies({get_session: override_get_session}):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/trials",
                headers={"Authorization": "Bearer fake-token"},
                json={
                    "title": "Backend Node Trial",
                    "role": "Backend Engineer",
                    "techStack": "Node.js, PostgreSQL",
                    "seniority": "Mid",
                    "focus": "Build new API feature and debug an issue",
                },
            )

    assert response.status_code == 409
    assert response.json()["detail"] == "Talent Partner onboarding required"
