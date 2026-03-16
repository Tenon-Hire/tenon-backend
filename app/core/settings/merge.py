from __future__ import annotations

import os
from collections.abc import Iterable

_SECTIONS: dict[str, tuple[list[str], str]] = {
    "database": (["DATABASE_URL", "DATABASE_URL_SYNC"], "TENON_"),
    "auth": (
        [
            "AUTH0_DOMAIN",
            "AUTH0_ISSUER",
            "AUTH0_JWKS_URL",
            "AUTH0_API_AUDIENCE",
            "AUTH0_ALGORITHMS",
            "AUTH0_JWKS_CACHE_TTL_SECONDS",
            "AUTH0_LEEWAY_SECONDS",
            "AUTH0_CLAIM_NAMESPACE",
            "AUTH0_EMAIL_CLAIM",
            "AUTH0_ROLES_CLAIM",
            "AUTH0_PERMISSIONS_CLAIM",
        ],
        "TENON_",
    ),
    "cors": (["CORS_ALLOW_ORIGINS", "CORS_ALLOW_ORIGIN_REGEX"], "TENON_"),
    "github": (
        [
            "GITHUB_API_BASE",
            "GITHUB_ORG",
            "GITHUB_TOKEN",
            "GITHUB_TEMPLATE_OWNER",
            "GITHUB_ACTIONS_WORKFLOW_FILE",
            "GITHUB_REPO_PREFIX",
            "GITHUB_CLEANUP_ENABLED",
            "WORKSPACE_RETENTION_DAYS",
            "WORKSPACE_CLEANUP_MODE",
            "WORKSPACE_DELETE_ENABLED",
            "GITHUB_WEBHOOK_SECRET",
            "GITHUB_WEBHOOK_MAX_BODY_BYTES",
        ],
        "TENON_",
    ),
    "email": (
        [
            "TENON_EMAIL_PROVIDER",
            "TENON_EMAIL_FROM",
            "TENON_RESEND_API_KEY",
            "SENDGRID_API_KEY",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_TLS",
        ],
        "",
    ),
    "storage_media": (
        [
            "MEDIA_STORAGE_PROVIDER",
            "MEDIA_S3_ENDPOINT",
            "MEDIA_S3_REGION",
            "MEDIA_S3_BUCKET",
            "MEDIA_S3_ACCESS_KEY_ID",
            "MEDIA_S3_SECRET_ACCESS_KEY",
            "MEDIA_S3_SESSION_TOKEN",
            "MEDIA_S3_USE_PATH_STYLE",
            "SIGNED_URL_EXPIRY_SECONDS",
            "MEDIA_SIGNED_URL_EXPIRES_SECONDS",
            "MEDIA_SIGNED_URL_MIN_SECONDS",
            "MEDIA_SIGNED_URL_MAX_SECONDS",
            "MEDIA_RETENTION_DAYS",
            "MEDIA_DELETE_ENABLED",
            "MEDIA_MAX_UPLOAD_BYTES",
            "MEDIA_ALLOWED_CONTENT_TYPES",
            "MEDIA_ALLOWED_EXTENSIONS",
        ],
        "TENON_",
    ),
}


def _merge_section(
    data: dict, section_key: str, keys: Iterable[str], *, env_prefix: str
) -> None:
    section = dict(data.get(section_key, {}) or {})
    for key in keys:
        env_key = f"{env_prefix}{key}"
        if key in data:
            section[key] = data.pop(key)
        elif key.lower() in data:
            section[key] = data.pop(key.lower())
        elif (env_val := os.getenv(env_key)) is not None:
            section[key] = env_val
    if section:
        data[section_key] = section


def merge_nested_settings(values: dict) -> dict:
    data = dict(values)
    for section_key, (keys, prefix) in _SECTIONS.items():
        _merge_section(data, section_key, keys, env_prefix=prefix)
    return data


__all__ = ["merge_nested_settings"]
