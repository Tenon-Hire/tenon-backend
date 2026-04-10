from __future__ import annotations

import pytest

import app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils as admin_demo
from app.shared.http.dependencies import (
    shared_http_dependencies_admin_demo_rules_utils as admin_rules,
)
from tests.shared.factories import create_talent_partner
from tests.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    patch_demo_settings,
    patch_get_principal,
    principal,
    request,
)


@pytest.mark.asyncio
async def test_require_demo_mode_admin_allows_winoe_roles_claim(
    async_session, monkeypatch
):
    patch_demo_settings(monkeypatch)
    patch_get_principal(
        monkeypatch,
        principal(
            email="admin-winoe-roles@test.com",
            sub="auth0|admin-winoe-roles",
            claims={"winoe_roles": ["admin"]},
        ),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "principal_admin"
    assert actor.actor_id == "auth0|admin-winoe-roles"


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
async def test_require_demo_mode_admin_allows_talent_partner_id_allowlist(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="allow-talent_partner-id@test.com"
    )
    await async_session.commit()
    patch_demo_settings(monkeypatch, talent_partner_ids=[talent_partner.id])
    patch_get_principal(
        monkeypatch,
        principal(
            email="allow-talent_partner-id@test.com",
            sub="auth0|allow-talent_partner-id",
            claims={},
        ),
    )
    actor = await admin_demo.require_demo_mode_admin(request(), None, async_session)
    assert actor.actor_type == "talent_partner_admin"
    assert actor.actor_id == str(talent_partner.id)
    assert actor.talent_partner_id == talent_partner.id


def test_admin_rules_normalized_tokens_skips_non_strings_and_blanks():
    assert admin_rules._normalized_tokens([" Admin ", "", "   ", 123, None]) == [
        "admin"
    ]
