from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_rejects_unapproved_alg(monkeypatch):
    auth0.clear_jwks_cache()
    monkeypatch.setattr(
        jwt, "get_unverified_header", lambda _t: {"kid": "kid1", "alg": "HS256"}
    )
    with pytest.raises(auth0.Auth0Error) as excinfo:
        auth0.decode_auth0_token("tok")
    assert "algorithm" in excinfo.value.detail
