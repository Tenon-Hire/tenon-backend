from __future__ import annotations

from app.config import settings

from .shared_http_middleware_http_config import (
    _coerce_string_list,
    _cors_config,
    _csrf_allowed_origins,
    _csrf_protected_prefixes,
    _default_csrf_path_prefixes,
    _env_name,
    _normalize_path_prefix,
)
from .shared_http_middleware_http_csrf_middleware import CsrfOriginEnforcementMiddleware
from .shared_http_middleware_http_request_middleware import (
    _headers_map,
    _is_cookie_authenticated_request,
    _normalize_origin,
    _path_matches_prefixes,
)
from .shared_http_middleware_http_setup_middleware import (
    configure_cors,
    configure_csrf_protection,
    configure_proxy_headers,
    configure_request_limits,
    configure_security_headers,
)

__all__ = [
    "CsrfOriginEnforcementMiddleware",
    "configure_csrf_protection",
    "configure_proxy_headers",
    "configure_request_limits",
    "configure_cors",
    "configure_security_headers",
    "_coerce_string_list",
    "_cors_config",
    "_csrf_allowed_origins",
    "_csrf_protected_prefixes",
    "_default_csrf_path_prefixes",
    "_env_name",
    "_normalize_path_prefix",
    "_headers_map",
    "_is_cookie_authenticated_request",
    "_normalize_origin",
    "_path_matches_prefixes",
    "settings",
]
