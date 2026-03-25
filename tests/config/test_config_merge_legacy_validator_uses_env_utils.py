from __future__ import annotations

from tests.config.config_test_utils import *


def test_merge_legacy_validator_uses_env(monkeypatch):
    monkeypatch.setenv("TENON_DATABASE_URL_SYNC", "postgresql://env-db")
    monkeypatch.setenv("TENON_AUTH0_ISSUER", "https://issuer.test")
    monkeypatch.setenv("TENON_CORS_ALLOW_ORIGIN_REGEX", "^https://allowed")
    values = {}
    merged = Settings._merge_legacy(values)
    assert merged["database"]["DATABASE_URL_SYNC"] == "postgresql://env-db"
    assert merged["auth"]["AUTH0_ISSUER"] == "https://issuer.test"
    assert merged["cors"]["CORS_ALLOW_ORIGIN_REGEX"] == "^https://allowed"
