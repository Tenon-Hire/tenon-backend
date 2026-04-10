from __future__ import annotations

from tests.config.config_test_utils import *


def test_settings_merge_env_prefers_env_values(monkeypatch):
    monkeypatch.setenv("WINOE_DATABASE_URL", "postgresql://env-db")
    monkeypatch.setenv("WINOE_CORS_ALLOW_ORIGIN_REGEX", "https://.*\\.example.com")
    s = Settings(database={}, cors={})
    assert s.database.DATABASE_URL == "postgresql://env-db"
    assert s.cors.CORS_ALLOW_ORIGIN_REGEX == "https://.*\\.example.com"
