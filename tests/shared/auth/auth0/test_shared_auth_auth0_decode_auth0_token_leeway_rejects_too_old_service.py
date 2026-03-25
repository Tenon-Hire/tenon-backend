from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_leeway_rejects_too_old(monkeypatch):
    auth0.clear_jwks_cache()
    secret = "test-secret"
    kid = "hs1"
    leeway_seconds = 30

    jwks = {
        "keys": [
            {
                "kid": kid,
                "kty": "oct",
                "k": base64url_encode(secret.encode("utf-8")).decode("ascii"),
                "alg": "HS256",
                "use": "sig",
            }
        ]
    }

    monkeypatch.setattr(auth0, "_fetch_jwks", lambda: jwks)
    monkeypatch.setattr(auth0.settings.auth, "AUTH0_ALGORITHMS", "HS256")
    monkeypatch.setattr(auth0.settings.auth, "AUTH0_API_AUDIENCE", "api://aud")
    monkeypatch.setattr(auth0.settings.auth, "AUTH0_ISSUER", "https://issuer.test/")
    monkeypatch.setattr(auth0.settings.auth, "AUTH0_LEEWAY_SECONDS", leeway_seconds)

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "auth0|leeway",
            "aud": auth0.settings.auth.audience,
            "iss": auth0.settings.auth.issuer,
            "exp": now - (leeway_seconds + 5),
        },
        secret,
        algorithm="HS256",
        headers={"kid": kid},
    )

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.decode_auth0_token(token)
    assert "expired" in str(exc.value.detail).lower()
