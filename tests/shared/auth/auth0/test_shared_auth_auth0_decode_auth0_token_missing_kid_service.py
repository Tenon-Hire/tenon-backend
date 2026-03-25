from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_decode_auth0_token_missing_kid(monkeypatch):
    monkeypatch.setattr(jwt, "get_unverified_header", lambda _t: {})

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.decode_auth0_token("tok")
    assert "kid" in str(exc.value.detail)
