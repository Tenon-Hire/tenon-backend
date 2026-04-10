from __future__ import annotations

import pytest
from sqlalchemy import func, select

import app.shared.auth.auth0 as auth0_module
from app.config import settings
from app.shared.auth import dependencies as security_deps
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.database.shared_database_models_model import User


async def _user_count(async_session) -> int:
    return int((await async_session.execute(select(func.count(User.id)))).scalar_one())


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(
    async_client, override_dependencies
):
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get("/api/trials")

    assert res.status_code == 401
    assert res.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_error_detail",
    [
        "Invalid signature",
        "Invalid audience",
        "Invalid token",
    ],
)
async def test_protected_route_invalid_tokens_return_401(
    async_client, override_dependencies, monkeypatch, auth_error_detail
):
    def bad_decode(_token: str):
        raise auth0_module.Auth0Error(auth_error_detail)

    monkeypatch.setattr(auth0_module, "decode_auth0_token", bad_decode)
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get(
            "/api/trials",
            headers={"Authorization": "Bearer invalid-token"},
        )

    assert res.status_code == 401
    assert res.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_protected_route_jwks_outage_returns_503(
    async_client, override_dependencies, monkeypatch
):
    def jwks_outage(_token: str):
        raise auth0_module.Auth0Error("Auth provider unavailable", status_code=503)

    monkeypatch.setattr(auth0_module, "decode_auth0_token", jwks_outage)
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get(
            "/api/trials",
            headers={"Authorization": "Bearer token-during-outage"},
        )

    assert res.status_code == 503
    assert res.json() == {"detail": "Auth provider unavailable"}


@pytest.mark.asyncio
async def test_valid_candidate_token_without_talent_partner_permission_returns_403_no_side_effect(
    async_client, async_session, override_dependencies, monkeypatch
):
    before_count = await _user_count(async_session)
    candidate_email = "candidate@example.com"

    def decode_candidate(_token: str):
        return {
            "sub": "auth0|candidate-1",
            "email": candidate_email,
            settings.auth.AUTH0_EMAIL_CLAIM: candidate_email,
            "permissions": ["candidate:access"],
            settings.auth.AUTH0_PERMISSIONS_CLAIM: ["candidate:access"],
        }

    monkeypatch.setattr(auth0_module, "decode_auth0_token", decode_candidate)
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get(
            "/api/trials",
            headers={"Authorization": "Bearer valid-candidate-token"},
        )

    after_count = await _user_count(async_session)
    assert res.status_code == 403
    assert res.json() == {"detail": "Talent Partner access required"}
    assert after_count == before_count
