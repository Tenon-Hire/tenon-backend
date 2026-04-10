from __future__ import annotations

import pytest

from tests.config.config_test_utils import *


def test_auth0_fail_fast_missing_issuer(monkeypatch):
    monkeypatch.setenv("WINOE_AUTH0_DOMAIN", "")
    monkeypatch.delenv("WINOE_AUTH0_ISSUER", raising=False)
    with pytest.raises(ValueError) as excinfo:
        Settings(_env_file=None, ENV="prod", AUTH0_API_AUDIENCE="api://aud")
    assert "AUTH0_ISSUER" in str(excinfo.value) or "AUTH0_DOMAIN" in str(excinfo.value)
