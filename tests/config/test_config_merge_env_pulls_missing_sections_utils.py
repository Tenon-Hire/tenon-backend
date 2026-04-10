from __future__ import annotations

from tests.config.config_test_utils import *


def test_merge_env_pulls_missing_sections(monkeypatch):
    monkeypatch.setenv("WINOE_DATABASE_URL", "postgresql://db")
    monkeypatch.setenv("WINOE_AUTH0_DOMAIN", "auth.example.com")
    monkeypatch.setenv("WINOE_CORS_ALLOW_ORIGINS", "https://a.com,https://b.com")
    monkeypatch.setenv("WINOE_GITHUB_ORG", "org")
    s = Settings()
    assert s.database.DATABASE_URL == "postgresql://db"
    assert s.auth.AUTH0_DOMAIN == "auth.example.com"
    assert ["https://a.com", "https://b.com"] == s.cors.CORS_ALLOW_ORIGINS
    assert s.github.GITHUB_ORG == "org"
