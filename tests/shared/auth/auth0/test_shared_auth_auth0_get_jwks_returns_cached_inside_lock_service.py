from __future__ import annotations

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_get_jwks_returns_cached_inside_lock(monkeypatch):
    auth0.clear_jwks_cache()
    auth0._jwks_cache["jwks"] = {"keys": [{"kid": "k1"}]}
    auth0._jwks_cache["fetched_at"] = 0.0
    times = iter([5000.0, 0.0])
    monkeypatch.setattr(auth0.time, "time", lambda: next(times))
    monkeypatch.setattr(auth0.settings.auth, "AUTH0_JWKS_CACHE_TTL_SECONDS", 3600)
    jwks = auth0.get_jwks()
    assert jwks["keys"][0]["kid"] == "k1"
