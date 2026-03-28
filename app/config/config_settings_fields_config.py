"""Application module for config settings fields config workflows."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_auth_config import AuthSettings
from .config_cors_config import CorsSettings
from .config_database_config import DatabaseSettings
from .config_email_config import EmailSettings
from .config_github_config import GithubSettings
from .config_storage_media_config import StorageMediaSettings


class SettingsFields(BaseSettings):
    """Represent settings fields data and behavior."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        env_nested_delimiter="__",
        env_prefix="TENON_",
    )

    ENV: str = "local"
    API_PREFIX: str = "/api"
    RATE_LIMIT_ENABLED: bool | None = None
    MAX_REQUEST_BODY_BYTES: int = 1_048_576
    DEBUG_PERF: bool = False
    PERF_SPANS_ENABLED: bool = False
    PERF_SQL_FINGERPRINTS_ENABLED: bool = False
    PERF_SPAN_SAMPLE_RATE: float = 1.0
    TRUSTED_PROXY_CIDRS: list[str] | str = Field(default_factory=list)
    DEMO_MODE: bool = False
    DEMO_ADMIN_ALLOWLIST_EMAILS: list[str] | str = Field(default_factory=list)
    DEMO_ADMIN_ALLOWLIST_SUBJECTS: list[str] | str = Field(default_factory=list)
    DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS: list[int] | str = Field(default_factory=list)
    DEMO_ADMIN_JOB_STALE_SECONDS: int = 900
    DEV_AUTH_BYPASS: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DEV_AUTH_BYPASS", "TENON_DEV_AUTH_BYPASS"),
    )
    SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED: bool = False

    DATABASE_URL: str | None = None
    DATABASE_URL_SYNC: str | None = None
    AUTH0_DOMAIN: str | None = None
    AUTH0_ISSUER: str | None = None
    AUTH0_JWKS_URL: str | None = None
    AUTH0_API_AUDIENCE: str | None = None
    AUTH0_ALGORITHMS: str | None = None
    CORS_ALLOW_ORIGINS: str | list[str] | None = None
    CORS_ALLOW_ORIGIN_REGEX: str | None = None
    CSRF_ALLOWED_ORIGINS: list[str] | str = Field(default_factory=list)
    CSRF_PROTECTED_PATH_PREFIXES: list[str] | str = Field(default_factory=list)

    GITHUB_API_BASE: str | None = None
    GITHUB_ORG: str | None = None
    GITHUB_TOKEN: str | None = None
    GITHUB_TEMPLATE_OWNER: str | None = None
    GITHUB_ACTIONS_WORKFLOW_FILE: str | None = None
    GITHUB_REPO_PREFIX: str | None = None
    GITHUB_CLEANUP_ENABLED: bool | None = None
    WORKSPACE_RETENTION_DAYS: int | None = None
    WORKSPACE_CLEANUP_MODE: str | None = None
    WORKSPACE_DELETE_ENABLED: bool | None = None
    GITHUB_WEBHOOK_SECRET: str | None = None
    GITHUB_WEBHOOK_MAX_BODY_BYTES: int | None = None

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    github: GithubSettings = Field(default_factory=GithubSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    storage_media: StorageMediaSettings = Field(default_factory=StorageMediaSettings)

    CANDIDATE_PORTAL_BASE_URL: str = ""
    ADMIN_API_KEY: str = ""
