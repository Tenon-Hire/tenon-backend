from __future__ import annotations

from tests.config.config_test_utils import *


def test_merge_legacy_prefers_env(monkeypatch):
    monkeypatch.setenv("WINOE_GITHUB_TOKEN", "t0k3n")
    monkeypatch.setenv("WINOE_GITHUB_ACTIONS_WORKFLOW_FILE", "evidence-capture.yml")
    monkeypatch.setenv("WINOE_WORKSPACE_RETENTION_DAYS", "15")
    monkeypatch.setenv("WINOE_WORKSPACE_CLEANUP_MODE", "archive")
    monkeypatch.setenv("WINOE_WORKSPACE_DELETE_ENABLED", "0")
    monkeypatch.setenv("WINOE_GITHUB_WEBHOOK_SECRET", "merge-secret")
    monkeypatch.setenv("WINOE_GITHUB_WEBHOOK_MAX_BODY_BYTES", "2048")
    monkeypatch.setenv("SMTP_PASSWORD", "supers3cret")
    merged = Settings._merge_legacy(
        {
            "database_url": "postgresql://db",
            "auth0_domain": "auth.example.com",
            "cors_allow_origin_regex": "^https://allowed",
            "github_api_base": "https://api.github.com",
            "email_provider": "smtp",
        }
    )
    assert merged["database"]["DATABASE_URL"] == "postgresql://db"
    assert merged["auth"]["AUTH0_DOMAIN"] == "auth.example.com"
    assert merged["cors"]["CORS_ALLOW_ORIGIN_REGEX"] == "^https://allowed"
    assert merged["github"]["GITHUB_API_BASE"] == "https://api.github.com"
    assert merged["github"]["GITHUB_TOKEN"] == "t0k3n"
    assert merged["github"]["GITHUB_ACTIONS_WORKFLOW_FILE"] == "evidence-capture.yml"
    assert merged["github"]["WORKSPACE_RETENTION_DAYS"] == "15"
    assert merged["github"]["WORKSPACE_CLEANUP_MODE"] == "archive"
    assert merged["github"]["WORKSPACE_DELETE_ENABLED"] == "0"
    assert merged["github"]["GITHUB_WEBHOOK_SECRET"] == "merge-secret"
    assert merged["github"]["GITHUB_WEBHOOK_MAX_BODY_BYTES"] == "2048"
    assert merged["email"]["SMTP_PASSWORD"] == "supers3cret"
