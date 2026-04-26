"""Application module for config github config workflows."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GithubSettings(BaseSettings):
    """GitHub integration configuration."""

    GITHUB_API_BASE: str = "https://api.github.com"
    GITHUB_ORG: str = "winoe-ai-repos"
    GITHUB_TOKEN: str = ""
    GITHUB_TEMPLATE_OWNER: str = "winoe-ai-repos"
    GITHUB_ACTIONS_WORKFLOW_FILE: str = "winoe-evidence-capture.yml"
    GITHUB_REPO_PREFIX: str = "winoe-ws-"
    GITHUB_CLEANUP_ENABLED: bool = False
    WORKSPACE_RETENTION_DAYS: int = 30
    WORKSPACE_CLEANUP_MODE: str = "archive"
    WORKSPACE_DELETE_ENABLED: bool = False
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_WEBHOOK_MAX_BODY_BYTES: int = 262_144

    @field_validator("WORKSPACE_RETENTION_DAYS")
    @classmethod
    def _validate_retention_days(cls, value: int) -> int:
        if value < 0:
            raise ValueError("WORKSPACE_RETENTION_DAYS must be >= 0")
        return value

    @field_validator("WORKSPACE_CLEANUP_MODE", mode="before")
    @classmethod
    def _normalize_cleanup_mode(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"archive", "delete"}:
            raise ValueError("WORKSPACE_CLEANUP_MODE must be 'archive' or 'delete'")
        return normalized

    model_config = SettingsConfigDict(extra="ignore", env_prefix="WINOE_")
