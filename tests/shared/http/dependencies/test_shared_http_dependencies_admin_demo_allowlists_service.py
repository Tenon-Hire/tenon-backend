from __future__ import annotations

import pytest

import app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils as admin_demo
from tests.shared.factories import create_recruiter
from tests.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    patch_demo_settings,
    patch_get_principal,
    principal,
    request,
)


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_tenon_roles_claim(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch)
    patch_get_principal(
        monkeypatch,
        principal(
            email="admin-tenon-roles@test.com",
            sub="auth0|admin-tenon-roles",
            claims={"tenon_roles": ["admin"]},
        ),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|admin-tenon-roles"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_email_allowlist(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch, emails=["allow@test.com"])
    patch_get_principal(
        monkeypatch,
        principal(email="allow@test.com", sub="auth0|allowlisted", claims={}),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|allowlisted"


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_subject_allowlist_with_blank_email(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch, subjects=["  auth0|allow-subject  "])
    patch_get_principal(
        monkeypatch,
        principal(email="", sub="auth0|allow-subject", claims={}),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
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
    patch_demo_settings(monkeypatch, recruiter_ids=[recruiter.id])
    patch_get_principal(
        monkeypatch,
        principal(
            email="allow-recruiter-id@test.com",
            sub="auth0|allow-recruiter-id",
            claims={},
        ),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "recruiter_admin"
    assert actor.actor_id == str(recruiter.id)
    assert actor.recruiter_id == recruiter.id
