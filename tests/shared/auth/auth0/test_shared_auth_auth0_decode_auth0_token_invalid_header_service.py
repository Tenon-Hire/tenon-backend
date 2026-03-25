from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_invalid_header(monkeypatch):
    def bad_header(_token):
        raise JWTError("bad header")

    monkeypatch.setattr(jwt, "get_unverified_header", bad_header)

    with pytest.raises(auth0.Auth0Error):
        auth0.decode_auth0_token("tok")
