import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.main import app
from app.shared.auth import auth0
from app.shared.auth import shared_auth_current_user_utils as current_user
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import Company, User
from app.shared.http.routes import shared_http_routes_auth_routes as auth_routes


@pytest.mark.asyncio
async def test_auth_me_creates_and_returns_user(
    async_session, monkeypatch, override_dependencies
):
    """Auth endpoint should decode token and create user if missing."""

    def fake_decode_auth0_token(_token: str) -> dict[str, str]:
        return {
            "email": "talent_partner@example.com",
            "name": "TalentPartner One",
            "sub": "auth0|test",
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
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "talent_partner@example.com"
    assert body["role"] == "talent_partner"
    assert body["companyId"] is None
    assert body["companyName"] is None
    assert body["onboardingComplete"] is False


@pytest.mark.asyncio
async def test_auth_me_returns_company_name_for_onboarded_talent_partner(
    async_session, monkeypatch, override_dependencies
):
    company = Company(name="Acme Recruiting")
    async_session.add(company)
    await async_session.flush()
    async_session.add(
        User(
            name="TalentPartner One",
            email="talent_partner@example.com",
            role="talent_partner",
            company_id=company.id,
            password_hash="",
        )
    )
    await async_session.commit()

    def fake_decode_auth0_token(_token: str) -> dict[str, str]:
        return {
            "email": "talent_partner@example.com",
            "name": "TalentPartner One",
            "sub": "auth0|test",
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
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["companyId"] == company.id
    assert body["companyName"] == "Acme Recruiting"
    assert body["onboardingComplete"] is True


@pytest.mark.asyncio
async def test_talent_partner_onboarding_assigns_company_and_updates_name(
    async_session, monkeypatch, override_dependencies
):
    def fake_decode_auth0_token(_token: str) -> dict[str, str]:
        return {
            "email": "signup@example.com",
            "name": "Signup Placeholder",
            "sub": "auth0|signup",
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
                "/api/auth/talent-partner-onboarding",
                headers={"Authorization": "Bearer fake-token"},
                json={
                    "name": "  Robel TalentPartner  ",
                    "companyName": "  Winoe Labs  ",
                },
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Robel TalentPartner"
    assert body["companyName"] == "Winoe Labs"
    assert body["onboardingComplete"] is True

    persisted_user = (
        await async_session.execute(
            select(User).where(User.email == "signup@example.com")
        )
    ).scalar_one()
    company = await async_session.get(Company, persisted_user.company_id)
    assert company is not None
    assert company.name == "Winoe Labs"


@pytest.mark.asyncio
async def test_auth_me_rate_limited_in_prod(
    async_session, monkeypatch, override_dependencies
):
    def fake_decode_auth0_token(_token: str) -> dict[str, str]:
        return {
            "email": "talent_partner@example.com",
            "name": "TalentPartner One",
            "sub": "auth0|test",
            "permissions": ["talent_partner:access"],
        }

    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )

    async def override_get_session():
        yield async_session

    monkeypatch.setattr(auth0, "decode_auth0_token", fake_decode_auth0_token)
    monkeypatch.setattr(current_user, "async_session_maker", session_maker)
    monkeypatch.setattr(settings, "ENV", "prod")
    auth_routes.rate_limit.limiter.reset()
    original_rule = auth_routes.AUTH_ME_RATE_LIMIT
    auth_routes.AUTH_ME_RATE_LIMIT = auth_routes.rate_limit.RateLimitRule(
        limit=1, window_seconds=60.0
    )

    with override_dependencies({get_session: override_get_session}):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            first = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer fake-token"},
            )
            second = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert first.status_code == 200, first.text
    assert second.status_code == 429

    auth_routes.AUTH_ME_RATE_LIMIT = original_rule
    auth_routes.rate_limit.limiter.reset()


@pytest.mark.asyncio
async def test_auth_logout_is_stateless(async_client):
    res = await async_client.post("/api/auth/logout")

    assert res.status_code == 204
    assert res.headers.get("cache-control") == "no-store"
    assert res.headers.get("pragma") == "no-cache"
    assert "set-cookie" not in res.headers
    assert res.headers.get("location") is None
