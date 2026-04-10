from __future__ import annotations

import pytest

from app.shared.auth import dependencies
from tests.shared.auth.dependencies.shared_auth_dependencies_utils import (
    ctx_maker,
    make_request,
)
from tests.shared.factories import create_talent_partner


@pytest.mark.asyncio
async def test_dev_bypass_allows_local_requests(async_session, monkeypatch):
    user = await create_talent_partner(async_session, email="dev@local.test")
    monkeypatch.setattr(dependencies, "_env_name", lambda: "local")
    result = await dependencies._dev_bypass_user(
        make_request({"x-dev-user-email": user.email}), async_session
    )
    assert result.email == user.email


@pytest.mark.asyncio
async def test_dev_bypass_rejects_non_localhost(async_session, monkeypatch):
    user = await create_talent_partner(async_session, email="remote@local.test")
    monkeypatch.setattr(dependencies, "_env_name", lambda: "local")
    with pytest.raises(Exception) as excinfo:
        await dependencies._dev_bypass_user(
            make_request({"x-dev-user-email": user.email}, host="10.0.0.1"),
            async_session,
        )
    assert "localhost" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_dev_bypass_guard_against_prod(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    monkeypatch.setattr(dependencies, "_env_name", lambda: "prod")
    with pytest.raises(RuntimeError):
        await dependencies._dev_bypass_user(
            make_request({"x-dev-user-email": "x@example.com"}), None
        )


def test_env_name_override(monkeypatch):
    monkeypatch.setitem(
        dependencies.sys.modules,
        "app.shared.auth.shared_auth_current_user_utils",
        type("m", (), {"_env_name": lambda: "override"}),
    )
    assert dependencies._env_name() == "override"


@pytest.mark.asyncio
async def test_dev_bypass_returns_none_when_header_missing(monkeypatch):
    monkeypatch.setattr(dependencies, "_env_name", lambda: "local")
    assert await dependencies._dev_bypass_user(make_request({}), None) is None


@pytest.mark.asyncio
async def test_dev_bypass_fallback_session_maker(monkeypatch):
    class DummySession:
        async def execute(self, *_a, **_k):
            class R:
                def scalar_one_or_none(self):
                    return None

            return R()

        async def commit(self):
            return None

    monkeypatch.setattr(dependencies, "_env_name", lambda: "local")
    monkeypatch.setitem(
        dependencies.sys.modules,
        "app.shared.auth.shared_auth_current_user_utils",
        type("mod", (), {"async_session_maker": ctx_maker(DummySession())}),
    )
    with pytest.raises(Exception) as excinfo:
        await dependencies._dev_bypass_user(
            make_request({"x-dev-user-email": "missing@example.com"}), None
        )
    assert "Dev user not found" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_prefers_dev_bypass(monkeypatch, async_session):
    dummy_user = object()

    async def _return_user(*_a, **_k):
        return dummy_user

    monkeypatch.setattr(dependencies, "_dev_bypass_user", _return_user)
    result = await dependencies.get_current_user(
        make_request({"x-dev-user-email": "dev@local.test"}), async_session, None
    )
    assert result is dummy_user


def test_env_helpers(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "ENV", "Prod")
    assert dependencies._env_name_base() == "prod"
    dependencies.sys.modules.pop("app.shared.auth.shared_auth_current_user_utils", None)
    assert dependencies._env_name() == "prod"


@pytest.mark.asyncio
async def test_dev_bypass_returns_none_for_prod_env(monkeypatch):
    monkeypatch.setattr(dependencies, "_env_name", lambda: "prod")
    assert (
        await dependencies._dev_bypass_user(
            make_request({"x-dev-user-email": "prod@local.test"}), None
        )
        is None
    )
