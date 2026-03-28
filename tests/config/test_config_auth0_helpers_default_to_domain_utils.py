from __future__ import annotations

from tests.config.config_test_utils import *


def test_auth0_helpers_default_to_domain():
    s = Settings(
        AUTH0_DOMAIN="example.auth0.com",
        AUTH0_ALGORITHMS="RS256, HS256",
        AUTH0_API_AUDIENCE="api://test",
        AUTH0_ISSUER="",
        AUTH0_JWKS_URL="",
    )

    assert s.auth0_issuer == "https://example.auth0.com/"
    assert s.auth0_jwks_url == "https://example.auth0.com/.well-known/jwks.json"
    assert s.auth0_algorithms == ["RS256", "HS256"]
