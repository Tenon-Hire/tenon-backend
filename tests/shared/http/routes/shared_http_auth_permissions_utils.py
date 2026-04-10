from __future__ import annotations

import pytest

import app.shared.auth.auth0 as auth0_module
from app.config import settings
from app.shared.auth import dependencies as security_deps
from app.shared.auth.dependencies import get_current_user
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.fixture(autouse=True)
def patch_auth0_decode(monkeypatch):
    """Parse shorthand tokens like talent_partner:email or candidate:email for tests."""

    def fake_decode(token: str):
        kind, email = token.split(":", 1) if ":" in token else ("candidate", token)
        perms: list[str] = []
        if kind == "talent_partner":
            perms = ["talent_partner:access"]
        elif kind == "candidate":
            perms = ["candidate:access"]
        email_claim = settings.auth.AUTH0_EMAIL_CLAIM
        permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
        claims = {
            "sub": f"{kind}|{email}",
            "email": email,
            email_claim: email,
            "permissions": perms,
            permissions_claim: perms,
        }
        if kind == "candidate":
            claims["email_verified"] = True
        return claims

    monkeypatch.setattr(auth0_module, "decode_auth0_token", fake_decode)


__all__ = [name for name in globals() if not name.startswith("__")]
