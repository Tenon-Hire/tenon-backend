from __future__ import annotations

from tests.config.config_test_utils import *


def test_github_settings_merge_flat_env():
    s = Settings(
        GITHUB_API_BASE="https://api.github.com",
        GITHUB_ORG="winoe",
        GITHUB_TOKEN="ghp_123",
        GITHUB_TEMPLATE_OWNER="winoe-templates",
        GITHUB_ACTIONS_WORKFLOW_FILE="evidence-capture.yml",
        GITHUB_REPO_PREFIX="prefix-",
        GITHUB_CLEANUP_ENABLED="True",
        WORKSPACE_RETENTION_DAYS=45,
        WORKSPACE_CLEANUP_MODE="delete",
        WORKSPACE_DELETE_ENABLED="True",
        GITHUB_WEBHOOK_SECRET="webhook-secret",
        GITHUB_WEBHOOK_MAX_BODY_BYTES=12345,
    )

    assert s.github.GITHUB_API_BASE == "https://api.github.com"
    assert s.github.GITHUB_ORG == "winoe"
    assert s.github.GITHUB_TOKEN == "ghp_123"
    assert s.github.GITHUB_TEMPLATE_OWNER == "winoe-templates"
    assert s.github.GITHUB_ACTIONS_WORKFLOW_FILE == "evidence-capture.yml"
    assert s.github.GITHUB_REPO_PREFIX == "prefix-"
    assert s.github.GITHUB_CLEANUP_ENABLED is True
    assert s.github.WORKSPACE_RETENTION_DAYS == 45
    assert s.github.WORKSPACE_CLEANUP_MODE == "delete"
    assert s.github.WORKSPACE_DELETE_ENABLED is True
    assert s.github.GITHUB_WEBHOOK_SECRET == "webhook-secret"
    assert s.github.GITHUB_WEBHOOK_MAX_BODY_BYTES == 12345
