from __future__ import annotations

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_auth_settings_properties_and_algorithms(monkeypatch):
    obj = auth0.settings.auth
    monkeypatch.setattr(obj, "AUTH0_DOMAIN", "tenant.auth0.com")
    monkeypatch.setattr(obj, "AUTH0_API_AUDIENCE", "api://aud")
    monkeypatch.setattr(obj, "AUTH0_ALGORITHMS", "RS256,HS256")
    assert obj.issuer.endswith("/")
    assert obj.jwks_url.endswith(".well-known/jwks.json")
    assert obj.algorithms == ["RS256", "HS256"]
