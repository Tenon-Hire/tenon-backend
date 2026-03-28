from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def _setup_valid_header_and_jwks(monkeypatch) -> None:
    auth0.clear_jwks_cache()
    monkeypatch.setattr(
        jwt, "get_unverified_header", lambda _t: {"kid": "kid1", "alg": "RS256"}
    )
    monkeypatch.setattr(auth0, "_fetch_jwks", lambda: {"keys": [{"kid": "kid1"}]})


def test_decode_auth0_token_invalid_not_before_claim(monkeypatch):
    _setup_valid_header_and_jwks(monkeypatch)

    def _bad_decode(*_args, **_kwargs):
        raise JWTError("nbf claim not satisfied")

    monkeypatch.setattr(jwt, "decode", _bad_decode)

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.decode_auth0_token("tok")

    assert "Invalid not-before claim" in str(exc.value.detail)


def test_decode_auth0_token_invalid_token_fallback(monkeypatch):
    _setup_valid_header_and_jwks(monkeypatch)

    def _bad_decode(*_args, **_kwargs):
        raise JWTError("token parsing failed")

    monkeypatch.setattr(jwt, "decode", _bad_decode)

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.decode_auth0_token("tok")

    assert "Invalid token" in str(exc.value.detail)
