from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.shared.auth import dependencies
from app.shared.auth.dependencies import (
    shared_auth_dependencies_users_utils as users_utils,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import User
from tests.shared.auth.dependencies.shared_auth_dependencies_utils import ctx_maker


@pytest.mark.asyncio
async def test_user_from_principal_creates_user(async_session):
    principal = type("P", (), {"email": "newuser@example.com", "name": "New User"})()
    user = await dependencies._user_from_principal(principal, async_session)
    assert user.email == principal.email


@pytest.mark.asyncio
async def test_user_from_principal_uses_session_maker(monkeypatch):
    principal = type("P", (), {"email": "maker@test.com", "name": "Maker"})()

    async def fake_lookup(db, email):
        return f"looked-{email}"

    monkeypatch.setattr(dependencies, "_lookup_user", fake_lookup)
    monkeypatch.setitem(
        dependencies.sys.modules,
        "app.shared.auth.shared_auth_current_user_utils",
        type("mod", (), {"async_session_maker": ctx_maker(object())}),
    )
    user = await dependencies._user_from_principal(principal, db=None)
    assert user == "looked-maker@test.com"


@pytest.mark.asyncio
async def test_user_from_principal_handles_integrity_error(monkeypatch):
    principal = type("P", (), {"email": "retry@test.com", "name": "Retry"})()
    lookup_calls = []

    async def fake_lookup(db, email):
        lookup_calls.append(email)
        return None if len(lookup_calls) == 1 else f"existing-{email}"

    class DummyDB:
        def __init__(self):
            self.rollbacks = 0
            self.commits = 0
            self.added = None

        def add(self, obj):
            self.added = obj

        async def commit(self):
            self.commits += 1
            raise IntegrityError("", "", "")

        async def rollback(self):
            self.rollbacks += 1

        async def refresh(self, obj):
            self.refreshed = obj

    db = DummyDB()
    monkeypatch.setattr(dependencies, "_lookup_user", fake_lookup)
    user = await dependencies._user_from_principal(principal, db)
    assert user == "existing-retry@test.com"
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_user_from_principal_assigns_candidate_role(async_session):
    principal = Principal(
        sub="auth0|candidate-role",
        email="candidate-role@example.com",
        name="Candidate Role",
        roles=["candidate"],
        permissions=[],
        claims={},
    )

    user = await dependencies._user_from_principal(principal, async_session)

    assert user.role == "candidate"


@pytest.mark.asyncio
async def test_user_from_principal_creates_local_talent_partner_with_company(
    async_session, monkeypatch
):
    principal = Principal(
        sub="auth0|local-talent_partner",
        email="local-talent_partner@local.test",
        name="Local TalentPartner",
        roles=["talent_partner"],
        permissions=["talent_partner:access"],
        claims={},
    )
    monkeypatch.setattr(users_utils, "env_name", lambda: "local")

    user = await dependencies._user_from_principal(principal, async_session)

    assert user.role == "talent_partner"
    assert user.company_id is not None


@pytest.mark.asyncio
async def test_user_from_principal_backfills_existing_local_talent_partner_without_company(
    async_session, monkeypatch
):
    talent_partner = User(
        name="Existing TalentPartner",
        email="existing-local@local.test",
        role="talent_partner",
        company_id=None,
        password_hash="",
    )
    async_session.add(talent_partner)
    await async_session.commit()

    principal = Principal(
        sub="auth0|existing-local",
        email=talent_partner.email,
        name=talent_partner.name,
        roles=["talent_partner"],
        permissions=["talent_partner:access"],
        claims={},
    )
    monkeypatch.setattr(users_utils, "env_name", lambda: "local")

    resolved = await dependencies._user_from_principal(principal, async_session)
    await async_session.refresh(talent_partner)

    assert resolved.id == talent_partner.id
    assert talent_partner.company_id is not None
