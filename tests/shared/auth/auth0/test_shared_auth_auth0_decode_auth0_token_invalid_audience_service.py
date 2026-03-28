from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_invalid_audience(monkeypatch):
    auth0.clear_jwks_cache()
    monkeypatch.setattr(
        jwt, "get_unverified_header", lambda _t: {"kid": "kid1", "alg": "RS256"}
    )

    def fake_fetch():
        return {"keys": [{"kid": "kid1"}]}

    monkeypatch.setattr(auth0, "_fetch_jwks", fake_fetch)

    def bad_decode(token, key, algorithms, audience, issuer, options):
        assert audience == auth0.settings.auth.audience
        raise JWTError("invalid audience")

    monkeypatch.setattr(jwt, "decode", bad_decode)

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.decode_auth0_token("tok")
    assert "audience" in str(exc.value.detail).lower()
