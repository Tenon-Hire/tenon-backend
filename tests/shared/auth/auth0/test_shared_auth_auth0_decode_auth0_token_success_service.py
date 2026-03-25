from __future__ import annotations

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_success(monkeypatch):
    auth0.clear_jwks_cache()
    monkeypatch.setattr(
        jwt, "get_unverified_header", lambda _t: {"kid": "kid1", "alg": "RS256"}
    )

    def fake_fetch():
        return {"keys": [{"kid": "kid1"}]}

    monkeypatch.setattr(auth0, "_fetch_jwks", fake_fetch)

    def ok_decode(token, key, algorithms, audience, issuer, options):
        assert isinstance(algorithms, list)
        assert "RS256" in algorithms
        assert options["leeway"] == auth0.settings.auth.AUTH0_LEEWAY_SECONDS
        return {"email": "ok@example.com"}

    monkeypatch.setattr(jwt, "decode", ok_decode)

    claims = auth0.decode_auth0_token("tok")
    assert claims["email"] == "ok@example.com"
