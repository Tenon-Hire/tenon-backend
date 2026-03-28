"""Application module for http middleware http config workflows."""

from __future__ import annotations

from app.config import settings

_LOCAL_DEFAULT_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


def _env_name() -> str:
    return str(getattr(settings, "ENV", "local") or "local").lower()


def _coerce_string_list(value) -> list[str]:
    if value in (None, "", [], (), "[]", "null", "None"):
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list | tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _cors_config() -> tuple[list[str], str | None]:
    cors_cfg = getattr(settings, "cors", None)
    origins = _coerce_string_list(
        getattr(cors_cfg, "CORS_ALLOW_ORIGINS", []) if cors_cfg else []
    )
    origin_regex = (getattr(cors_cfg, "CORS_ALLOW_ORIGIN_REGEX", None) or "").strip()
    if not origins and not origin_regex and _env_name() in {"local", "test"}:
        origins = list(_LOCAL_DEFAULT_ORIGINS)
    return origins, (origin_regex or None)


def _normalize_path_prefix(prefix: str) -> str:
    normalized = (prefix or "").strip()
    if not normalized:
        return ""
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def _default_csrf_path_prefixes() -> list[str]:
    api_prefix_raw = getattr(settings, "API_PREFIX", None)
    api_prefix = _normalize_path_prefix(
        str("/api" if api_prefix_raw is None else api_prefix_raw)
    )
    return [api_prefix or "/"]


def _csrf_protected_prefixes() -> list[str]:
    configured = _coerce_string_list(
        getattr(settings, "CSRF_PROTECTED_PATH_PREFIXES", [])
    )
    prefixes = configured or _default_csrf_path_prefixes()
    normalized: list[str] = []
    seen: set[str] = set()
    for prefix in prefixes:
        value = _normalize_path_prefix(prefix)
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _csrf_allowed_origins() -> list[str]:
    configured = _coerce_string_list(getattr(settings, "CSRF_ALLOWED_ORIGINS", []))
    if configured:
        return configured
    cors_origins, _ = _cors_config()
    if cors_origins:
        return cors_origins
    if _env_name() in {"local", "test"}:
        return list(_LOCAL_DEFAULT_ORIGINS)
    return []
