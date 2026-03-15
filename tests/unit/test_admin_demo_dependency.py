from __future__ import annotations

import pytest
from fastapi import HTTPException, Request

import app.api.dependencies.admin_demo as admin_demo
from app.core.auth.principal import Principal
from app.core.settings import settings
from tests.factories import create_recruiter


def _principal(
    *,
    email: str,
    sub: str,
    roles: list[str] | None = None,
    claims: dict | None = None,
) -> Principal:
    payload = {"sub": sub, "email": email}
    if claims:
        payload.update(claims)
    return Principal(
        sub=sub,
        email=email,
        name="admin",
        roles=roles or [],
        permissions=["recruiter:access"],
        claims=payload,
    )


def _request() -> Request:
    scope = {
        "type": "http",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "path": "/api/admin/jobs/job/requeue",
        "method": "POST",
        "query_string": b"",
        "server": ("testserver", 80),
    }

    async def _receive():
        return {"type": "http.request"}

    return Request(scope, _receive)


def _patch_get_principal(monkeypatch, principal: Principal) -> None:
    async def _fake_get_principal(_credentials, _request):
        return principal

    monkeypatch.setattr(admin_demo, "get_principal", _fake_get_principal)


@pytest.mark.asyncio
async def test_require_demo_mode_admin_returns_404_when_demo_mode_off(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", False)

    with pytest.raises(HTTPException) as excinfo:
        await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_admin_role_claim(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    principal = _principal(
        email="admin-role@test.com",
        sub="auth0|admin-role",
        claims={"role": "admin"},
    )
    _patch_get_principal(monkeypatch, principal)

    actor = await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|admin-role"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_tenon_roles_claim(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    principal = _principal(
        email="admin-tenon-roles@test.com",
        sub="auth0|admin-tenon-roles",
        claims={"tenon_roles": ["admin"]},
    )
    _patch_get_principal(monkeypatch, principal)

    actor = await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|admin-tenon-roles"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_email_allowlist(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", ["allow@test.com"])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    principal = _principal(
        email="allow@test.com",
        sub="auth0|allowlisted",
        claims={},
    )
    _patch_get_principal(monkeypatch, principal)

    actor = await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|allowlisted"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_subject_allowlist_with_blank_email(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", [])
    monkeypatch.setattr(
        settings,
        "DEMO_ADMIN_ALLOWLIST_SUBJECTS",
        ["  auth0|allow-subject  "],
    )
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    principal = _principal(
        email="",
        sub="auth0|allow-subject",
        claims={},
    )
    _patch_get_principal(monkeypatch, principal)

    actor = await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|allow-subject"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_recruiter_id_allowlist(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="allow-recruiter-id@test.com"
    )
    await async_session.commit()

    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [recruiter.id])
    principal = _principal(
        email="allow-recruiter-id@test.com",
        sub="auth0|allow-recruiter-id",
        claims={},
    )
    _patch_get_principal(monkeypatch, principal)

    actor = await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert actor.actor_type == "recruiter_admin"
    assert actor.actor_id == str(recruiter.id)
    assert actor.recruiter_id == recruiter.id


@pytest.mark.asyncio
async def test_require_demo_mode_admin_rejects_non_admin(async_session, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    principal = _principal(
        email="no-admin@test.com",
        sub="auth0|no-admin",
        claims={},
    )
    _patch_get_principal(monkeypatch, principal)

    with pytest.raises(HTTPException) as excinfo:
        await admin_demo.require_demo_mode_admin(_request(), None, async_session)
    assert excinfo.value.status_code == 403
