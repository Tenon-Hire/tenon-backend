from __future__ import annotations

import asyncio

import pytest_asyncio
from fastapi import HTTPException, Request, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.main import app
from app.shared.auth.principal import Principal, get_principal
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from tests.shared.fixtures.shared_fixtures_github_stub_client import StubGithubClient


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    async def override_get_session():
        yield db_session

    async def override_get_current_user(request: Request) -> User:
        email = (request.headers.get("x-dev-user-email") or "").strip()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing x-dev-user-email header",
            )
        user = (
            await db_session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Dev user not found: {email}. Seed this user in the DB first.",
            )
        return user

    async def override_get_principal(request: Request) -> Principal:
        auth_header = (request.headers.get("Authorization") or "").strip()
        kind, email = "candidate", None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            kind, email = token.split(":", 1) if ":" in token else ("candidate", token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
        perms = (
            ["talent_partner:access"]
            if kind == "talent_partner"
            else ["candidate:access"]
            if kind == "candidate"
            else [kind]
        )
        claims = {
            "sub": f"{kind}-{email}",
            "email": email,
            settings.auth.AUTH0_EMAIL_CLAIM: email,
            "permissions": perms,
            settings.auth.AUTH0_PERMISSIONS_CLAIM: perms,
        }
        if kind == "candidate":
            claims["email_verified"] = True
        return Principal(
            sub=f"{kind}-{email}",
            email=email,
            name=email.split("@")[0],
            roles=[],
            permissions=perms,
            claims=claims,
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_principal] = override_get_principal
    app.dependency_overrides[get_github_client] = lambda: StubGithubClient()
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    await asyncio.sleep(0)
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_principal, None)
    app.dependency_overrides.pop(get_github_client, None)
