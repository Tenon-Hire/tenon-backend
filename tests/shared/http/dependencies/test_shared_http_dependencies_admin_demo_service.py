from __future__ import annotations

import pytest
from fastapi import HTTPException

import app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils as admin_demo
from tests.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    patch_demo_settings,
    patch_get_principal,
    principal,
    request,
)


@pytest.mark.asyncio
async def test_require_demo_mode_admin_returns_404_when_demo_mode_off(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch, demo_mode=False)
    with pytest.raises(HTTPException) as excinfo:
        await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_admin_role_claim(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch)
    patch_get_principal(
        monkeypatch,
        principal(
            email="admin-role@test.com",
            sub="auth0|admin-role",
            claims={"role": "admin"},
        ),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|admin-role"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_rejects_non_admin(async_session, monkeypatch):
    patch_demo_settings(monkeypatch)
    patch_get_principal(
        monkeypatch,
        principal(email="no-admin@test.com", sub="auth0|no-admin", claims={}),
    )
    with pytest.raises(HTTPException) as excinfo:
        await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert excinfo.value.status_code == 403
