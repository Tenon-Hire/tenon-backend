from __future__ import annotations

from app.services.tasks.template_catalog_data import (
    ALLOWED_TEMPLATE_KEYS,
    DEFAULT_TEMPLATE_KEY,
    LEGACY_TEMPLATE_REPO_REWRITES,
    TEMPLATE_CATALOG,
)


class TemplateKeyError(ValueError):
    """Raised when a template key is invalid."""


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


def validate_template_key(template_key: str) -> str:
    if not isinstance(template_key, str):
        raise TemplateKeyError("templateKey must be a string")
    normalized = template_key.strip()
    canonical = TEMPLATE_KEY_ALIASES.get(normalized)
    if canonical is None:
        allowed = ", ".join(sorted(ALLOWED_TEMPLATE_KEYS))
        raise TemplateKeyError(f"Invalid templateKey. Allowed values: {allowed}")
    return canonical


def resolve_template_repo_full_name(template_key: str) -> str:
    return TEMPLATE_CATALOG[validate_template_key(template_key)]["repo_full_name"]


def normalize_template_repo_value(
    template_repo: str | None, *, template_key: str | None = None
) -> str | None:
    template_repo = (template_repo or "").strip()
    validated_key: str | None = None
    if template_key:
        try:
            validated_key = validate_template_key(template_key)
        except TemplateKeyError:
            validated_key = None
    default_repo = resolve_template_repo_full_name(DEFAULT_TEMPLATE_KEY)
    if template_repo in LEGACY_TEMPLATE_REPO_REWRITES:
        return (
            resolve_template_repo_full_name(validated_key)
            if validated_key
            else default_repo
        )
    if template_repo:
        return template_repo
    if validated_key:
        return resolve_template_repo_full_name(validated_key)
    return None
