from __future__ import annotations

import logging
from urllib.parse import urlsplit

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.proxy_headers import TrustedProxyHeadersMiddleware, trusted_proxy_cidrs
from app.core.request_limits import RequestSizeLimitMiddleware
from app.core.settings import settings

_LOCAL_DEFAULT_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_ORIGIN_MISMATCH_RESPONSE = {
    "error": "CSRF_ORIGIN_MISMATCH",
    "message": "Request origin not allowed.",
}

logger = logging.getLogger(__name__)


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
    if api_prefix_raw is None:
        api_prefix_raw = "/api"
    api_prefix = _normalize_path_prefix(str(api_prefix_raw))
    # Align CSRF scope with registered API routes so the default is never inert.
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


def _headers_map(raw_headers) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in raw_headers or []:
        decoded_key = key.decode("latin1").lower()
        if decoded_key not in headers:
            headers[decoded_key] = value.decode("latin1")
    return headers


def _normalize_origin(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if scheme not in {"http", "https"} or not host:
        return None
    if parsed.username or parsed.password:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    default_port = 80 if scheme == "http" else 443
    host_display = f"[{host}]" if ":" in host else host
    if port in (None, default_port):
        return f"{scheme}://{host_display}"
    return f"{scheme}://{host_display}:{port}"


def _is_cookie_authenticated_request(headers: dict[str, str]) -> bool:
    return bool((headers.get("cookie") or "").strip())


def _path_matches_prefixes(path: str, prefixes: list[str]) -> bool:
    normalized_path = path or "/"
    for prefix in prefixes:
        if prefix == "/":
            return True
        if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
            return True
    return False


class CsrfOriginEnforcementMiddleware:
    def __init__(
        self,
        app,
        *,
        allowed_origins: list[str] | None = None,
        protected_path_prefixes: list[str] | None = None,
    ) -> None:
        self.app = app
        self.allowed_origins = {
            normalized
            for origin in (allowed_origins or [])
            if (normalized := _normalize_origin(origin))
        }
        self.protected_path_prefixes = [
            prefix
            for prefix in (
                _normalize_path_prefix(p) for p in (protected_path_prefixes or [])
            )
            if prefix
        ]

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "").upper()
        if method not in _STATE_CHANGING_METHODS:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        if not _path_matches_prefixes(path, self.protected_path_prefixes):
            await self.app(scope, receive, send)
            return

        headers = _headers_map(scope.get("headers") or [])
        if not _is_cookie_authenticated_request(headers):
            await self.app(scope, receive, send)
            return

        raw_origin = (headers.get("origin") or "").strip()
        raw_referer = (headers.get("referer") or "").strip()
        origin = _normalize_origin(raw_origin) if raw_origin else None
        referer_origin = _normalize_origin(raw_referer) if raw_referer else None
        observed_origin = origin if raw_origin else referer_origin

        if observed_origin not in self.allowed_origins:
            logger.warning(
                "csrf_origin_mismatch",
                extra={
                    "method": method,
                    "path": path,
                    "origin": raw_origin or None,
                    "referer_origin": referer_origin,
                },
            )
            response = JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=dict(_CSRF_ORIGIN_MISMATCH_RESPONSE),
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def configure_proxy_headers(app: FastAPI) -> None:
    cidrs = trusted_proxy_cidrs()
    if cidrs:
        app.add_middleware(TrustedProxyHeadersMiddleware, trusted_proxy_cidrs=cidrs)


def configure_request_limits(app: FastAPI) -> None:
    app.add_middleware(
        RequestSizeLimitMiddleware, max_body_bytes=settings.MAX_REQUEST_BODY_BYTES
    )


def configure_csrf_protection(app: FastAPI) -> None:
    app.add_middleware(
        CsrfOriginEnforcementMiddleware,
        allowed_origins=_csrf_allowed_origins(),
        protected_path_prefixes=_csrf_protected_prefixes(),
    )


def configure_cors(app: FastAPI) -> None:
    origins, origin_regex = _cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


__all__ = [
    "CsrfOriginEnforcementMiddleware",
    "configure_csrf_protection",
    "configure_proxy_headers",
    "configure_request_limits",
    "configure_cors",
]
