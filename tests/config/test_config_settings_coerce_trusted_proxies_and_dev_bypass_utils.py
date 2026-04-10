from __future__ import annotations

from tests.config.config_test_utils import *


def test_settings_coerce_trusted_proxies_and_dev_bypass(monkeypatch):
    monkeypatch.setenv("WINOE_DEV_AUTH_BYPASS", "1")
    s = Settings(
        DATABASE_URL="postgresql://localhost/winoe_test",
        AUTH0_DOMAIN="example.auth0.com",
        AUTH0_API_AUDIENCE="aud",
        TRUSTED_PROXY_CIDRS="10.0.0.0/8",
        ENV="test",
    )
    assert s._coerce_trusted_proxy_cidrs("10.0.0.0/8") == ["10.0.0.0/8"]
    assert s.dev_auth_bypass_enabled is True
    prod_settings = Settings(
        DATABASE_URL="postgresql://localhost/winoe_test",
        AUTH0_DOMAIN="example.auth0.com",
        AUTH0_API_AUDIENCE="aud",
        CORS_ALLOW_ORIGINS=["https://frontend.winoe.ai"],
        ENV="prod",
    )
    assert prod_settings.dev_auth_bypass_enabled is True
