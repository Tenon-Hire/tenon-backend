from __future__ import annotations

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_refreshes_jwks_on_kid_miss(monkeypatch):
    auth0.clear_jwks_cache()
    monkeypatch.setattr(
        jwt, "get_unverified_header", lambda _t: {"kid": "kid2", "alg": "RS256"}
    )

    responses = [{"keys": [{"kid": "kid1"}]}, {"keys": [{"kid": "kid2"}]}]

    def fake_fetch():
        return responses.pop(0)

    monkeypatch.setattr(auth0, "_fetch_jwks", fake_fetch)

    def ok_decode(token, key, algorithms, audience, issuer, options):
        return {"email": "ok@example.com"}

    monkeypatch.setattr(jwt, "decode", ok_decode)

    claims = auth0.decode_auth0_token("tok")
    assert claims["email"] == "ok@example.com"
