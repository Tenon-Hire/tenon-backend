from __future__ import annotations

from tests.config.config_test_utils import *


def test_settings_merge_env(monkeypatch):
    monkeypatch.setenv("WINOE_AUTH0_DOMAIN", "env-domain.auth0.com")
    monkeypatch.setenv("WINOE_CORS_ALLOW_ORIGINS", '["https://a.com"]')
    monkeypatch.setenv("WINOE_GITHUB_API_BASE", "https://api.github.com")
    s = Settings()
    assert s.auth.AUTH0_DOMAIN == "env-domain.auth0.com"
    assert ["https://a.com"] == s.cors.CORS_ALLOW_ORIGINS
    assert s.github.GITHUB_API_BASE == "https://api.github.com"
