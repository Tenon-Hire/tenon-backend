"""Application module for init workflows."""

from __future__ import annotations

from .config_app_config import Settings

# NOTE: This package keeps env parsing centralized while feature-scoped configs land.
from .config_auth_config import AuthSettings
from .config_claims_config import claim_namespace, claim_uri
from .config_cors_config import CorsSettings
from .config_database_config import DatabaseSettings
from .config_defaults_config import (
    DEFAULT_CLAIM_NAMESPACE,
    normalize_sync_url,
    to_async_url,
)
from .config_email_config import EmailSettings
from .config_github_config import GithubSettings
from .config_parsers_config import parse_env_list
from .config_storage_media_config import StorageMediaSettings

_normalize_sync_url = normalize_sync_url
_to_async_url = to_async_url

settings = Settings()

__all__ = [
    "AuthSettings",
    "CorsSettings",
    "DatabaseSettings",
    "DEFAULT_CLAIM_NAMESPACE",
    "EmailSettings",
    "GithubSettings",
    "Settings",
    "claim_namespace",
    "claim_uri",
    "parse_env_list",
    "settings",
    "StorageMediaSettings",
    "normalize_sync_url",
    "to_async_url",
    "_normalize_sync_url",
    "_to_async_url",
]
