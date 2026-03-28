from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.shared.auth import dependencies
from app.shared.auth.principal import Principal
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
