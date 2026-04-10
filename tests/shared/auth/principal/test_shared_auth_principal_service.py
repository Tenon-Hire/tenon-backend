from typing import ClassVar

import pytest
from fastapi import HTTPException

from app.config import settings
from app.shared.auth import principal


def test_extract_principal_missing_email_claim():
    claims = {"sub": "auth0|123", "permissions": ["candidate:access"]}
    with pytest.raises(HTTPException) as excinfo:
        principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert excinfo.value.status_code == 401
    assert "Invalid token" in excinfo.value.detail


def test_extract_principal_missing_email_claim_config(monkeypatch):
    claims = {"sub": "auth0|123", "permissions": ["candidate:access"]}
    monkeypatch.setattr(settings.auth, "AUTH0_EMAIL_CLAIM", "")
    with pytest.raises(HTTPException) as excinfo:
        principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert excinfo.value.status_code == 500
    assert "AUTH0_EMAIL_CLAIM not configured" in excinfo.value.detail


def test_permissions_from_namespaced_claim(monkeypatch):
    monkeypatch.setattr(settings.auth, "AUTH0_EMAIL_CLAIM", "https://winoe.ai/email")
    monkeypatch.setattr(
        settings.auth, "AUTH0_PERMISSIONS_CLAIM", "https://winoe.ai/permissions"
    )
    claims = {
        "sub": "auth0|abc",
        "https://winoe.ai/email": "jane@example.com",
        "https://winoe.ai/permissions": ["candidate:access"],
    }
    p = principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert "candidate:access" in p.permissions


def test_permissions_from_namespaced_string_claim(monkeypatch):
    monkeypatch.setattr(settings.auth, "AUTH0_EMAIL_CLAIM", "https://winoe.ai/email")
    claims = {
        "sub": "auth0|abc",
        "https://winoe.ai/email": "jane@example.com",
        "https://winoe.ai/permissions_str": "candidate:access talent_partner:access",
    }
    p = principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert "candidate:access" in p.permissions
    assert "talent_partner:access" in p.permissions


def test_permissions_from_roles_mapping(monkeypatch):
    monkeypatch.setattr(settings.auth, "AUTH0_EMAIL_CLAIM", "https://winoe.ai/email")
    monkeypatch.setattr(settings.auth, "AUTH0_ROLES_CLAIM", "https://winoe.ai/roles")
    claims = {
        "sub": "auth0|abc",
        "https://winoe.ai/email": "talent_partner@example.com",
        "https://winoe.ai/roles": ["senior-talent_partner"],
    }
    p = principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert "talent_partner:access" in p.permissions


def test_extract_principal_supports_url_claim_keys(monkeypatch):
    monkeypatch.setattr(settings.auth, "AUTH0_EMAIL_CLAIM", "https://winoe.ai/email")
    monkeypatch.setattr(
        settings.auth, "AUTH0_PERMISSIONS_CLAIM", "https://winoe.ai/permissions"
    )
    claims = {
        "sub": "auth0|winoe123",
        "https://winoe.ai/email": "x@y.com",
        "https://winoe.ai/permissions": ["talent_partner:access"],
    }
    p = principal._extract_principal(claims)  # type: ignore[attr-defined]
    assert p.email == "x@y.com"
    assert "talent_partner:access" in p.permissions


@pytest.mark.asyncio
async def test_require_permissions_blocks_missing():
    dep = principal.require_permissions(["needed"])

    class DummyPrincipal:
        permissions: ClassVar[list[str]] = []

    with pytest.raises(HTTPException):
        await dep(DummyPrincipal())  # type: ignore[arg-type]

    class HasPerms:
        permissions: ClassVar[list[str]] = ["needed"]

    result = await dep(HasPerms())  # type: ignore[arg-type]
    assert result.permissions == ["needed"]
