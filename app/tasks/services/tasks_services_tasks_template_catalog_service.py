"""Application module for tasks services tasks template catalog service workflows."""

from __future__ import annotations

from app.tasks.services.tasks_services_tasks_template_catalog_constants import (
    ALLOWED_TEMPLATE_KEYS,
    LEGACY_TEMPLATE_REPO_REWRITES,
    TEMPLATE_CATALOG,
)
from app.tasks.services.tasks_services_tasks_template_catalog_constants import (
    DEFAULT_TEMPLATE_KEY as _DEFAULT_TEMPLATE_KEY,
)


class TemplateKeyError(ValueError):
    """Raised when a template key is invalid."""


DEFAULT_TEMPLATE_KEY = _DEFAULT_TEMPLATE_KEY


def _canonical_key_from_repo(repo_full_name: str) -> str | None:
    for key, meta in TEMPLATE_CATALOG.items():
        if meta["repo_full_name"] == repo_full_name:
            return key
    return None


def _build_template_key_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for key, meta in TEMPLATE_CATALOG.items():
        aliases[key] = key
        repo_full_name = (meta.get("repo_full_name") or "").strip()
        if repo_full_name:
            aliases[repo_full_name] = key
            aliases[repo_full_name.rsplit("/", 1)[-1]] = key
    for legacy_repo, rewritten_repo in LEGACY_TEMPLATE_REPO_REWRITES.items():
        canonical = _canonical_key_from_repo(rewritten_repo)
        if canonical:
            aliases.setdefault(legacy_repo, canonical)
            aliases.setdefault(legacy_repo.rsplit("/", 1)[-1], canonical)
    return aliases


TEMPLATE_KEY_ALIASES = _build_template_key_aliases()


def _template_key_from_repo_value(repo_full_name: str | None) -> str | None:
    repo_value = (repo_full_name or "").strip()
    if not repo_value:
        return None
    for candidate in (repo_value, repo_value.rsplit("/", 1)[-1]):
        try:
            return validate_template_key(candidate)
        except TemplateKeyError:
            continue
    return None


def validate_template_key(template_key: str) -> str:
    """Validate template key."""
    if not isinstance(template_key, str):
        raise TemplateKeyError("templateKey must be a string")
    normalized = template_key.strip()
    canonical = TEMPLATE_KEY_ALIASES.get(normalized)
    if canonical is None:
        allowed = ", ".join(sorted(ALLOWED_TEMPLATE_KEYS))
        raise TemplateKeyError(f"Invalid templateKey. Allowed values: {allowed}")
    return canonical


def resolve_template_repo_full_name(template_key: str) -> str:
    """Resolve template repo full name."""
    return TEMPLATE_CATALOG[validate_template_key(template_key)]["repo_full_name"]


def normalize_template_repo_value(
    template_repo: str | None, *, template_key: str | None = None
) -> str | None:
    """Normalize template repo value."""
    template_repo = (template_repo or "").strip()
    validated_key: str | None = None
    if template_key:
        try:
            validated_key = validate_template_key(template_key)
        except TemplateKeyError:
            validated_key = None
    if template_repo in LEGACY_TEMPLATE_REPO_REWRITES:
        if template_repo in {
            "winoe-templates/node-day2-api",
            "winoe-templates/node-day3-debug",
            "winoe-dev/winoe-template-python",
        }:
            return (
                resolve_template_repo_full_name(validated_key)
                if validated_key
                else LEGACY_TEMPLATE_REPO_REWRITES[template_repo]
            )
        return LEGACY_TEMPLATE_REPO_REWRITES[template_repo]
    if template_repo:
        canonical_key = _template_key_from_repo_value(template_repo)
        if canonical_key:
            return resolve_template_repo_full_name(canonical_key)
        return template_repo
    if validated_key:
        return resolve_template_repo_full_name(validated_key)
    return None
