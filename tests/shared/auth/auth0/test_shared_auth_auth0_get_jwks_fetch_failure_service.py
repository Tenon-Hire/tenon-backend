from __future__ import annotations

import pytest

from tests.shared.auth.auth0.shared_auth_auth0_utils import *


def test_get_jwks_fetch_failure(monkeypatch):
    auth0.clear_jwks_cache()

    def bad_fetch():
        raise auth0.httpx.ConnectError("down")

    monkeypatch.setattr(auth0, "_fetch_jwks", bad_fetch)

    with pytest.raises(auth0.Auth0Error) as exc:
        auth0.get_jwks()
    assert exc.value.status_code == 503
