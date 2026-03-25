from __future__ import annotations

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_get_jwks_fetches_and_caches(monkeypatch):
    auth0.clear_jwks_cache()

    calls = []

    def fake_fetch():
        calls.append("fetch")
        return {"keys": [{"kid": "k1"}]}

    monkeypatch.setattr(auth0, "_fetch_jwks", fake_fetch)

    jwks = auth0.get_jwks()
    assert jwks["keys"][0]["kid"] == "k1"
    assert calls == ["fetch"]

    jwks = auth0.get_jwks()
    assert jwks["keys"][0]["kid"] == "k1"
    assert calls == ["fetch"]
