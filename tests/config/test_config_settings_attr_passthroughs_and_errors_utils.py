from __future__ import annotations

import pytest

from tests.config.config_test_utils import *


def test_settings_attr_passthroughs_and_errors():
    s = Settings(
        AUTH0_DOMAIN="example.auth0.com",
        AUTH0_JWKS_URL="https://example.auth0.com/.well-known/jwks.json",
    )
    # __setattr__/__getattr__ passthrough
    s.AUTH0_JWKS_URL = "https://override.test/jwks.json"

    with pytest.raises(AttributeError):
        _ = s.MISSING_FIELD

    assert s.auth.AUTH0_JWKS_URL == "https://override.test/jwks.json"
