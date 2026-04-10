from __future__ import annotations

from tests.config.config_test_utils import *


def test_merge_env_applies_nested_values(monkeypatch):
    monkeypatch.setenv("WINOE_DATABASE_URL_SYNC", "postgresql://env-sync")
    monkeypatch.setenv("WINOE_AUTH0_API_AUDIENCE", "api://aud")
    monkeypatch.setenv("WINOE_CORS_ALLOW_ORIGIN_REGEX", "^https://allowed")
    s = Settings(database={}, auth={}, cors={})
    assert s.database.DATABASE_URL_SYNC == "postgresql://env-sync"
    assert s.auth.AUTH0_API_AUDIENCE == "api://aud"
    assert s.cors.CORS_ALLOW_ORIGIN_REGEX == "^https://allowed"
