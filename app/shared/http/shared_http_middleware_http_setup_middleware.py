"""Application module for http middleware http setup middleware workflows."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.shared.utils.shared_utils_proxy_headers_utils import (
    TrustedProxyHeadersMiddleware,
    trusted_proxy_cidrs,
)
from app.shared.utils.shared_utils_request_limits_utils import (
    RequestSizeLimitMiddleware,
)

from .shared_http_middleware_http_config import (
    _cors_config,
    _csrf_allowed_origins,
    _csrf_protected_prefixes,
)
from .shared_http_middleware_http_csrf_middleware import CsrfOriginEnforcementMiddleware


def configure_proxy_headers(app: FastAPI) -> None:
    """Execute configure proxy headers."""
    cidrs = trusted_proxy_cidrs()
    if cidrs:
        app.add_middleware(TrustedProxyHeadersMiddleware, trusted_proxy_cidrs=cidrs)


def configure_request_limits(app: FastAPI) -> None:
    """Execute configure request limits."""
    app.add_middleware(
        RequestSizeLimitMiddleware, max_body_bytes=settings.MAX_REQUEST_BODY_BYTES
    )


def configure_csrf_protection(app: FastAPI) -> None:
    """Execute configure csrf protection."""
    app.add_middleware(
        CsrfOriginEnforcementMiddleware,
        allowed_origins=_csrf_allowed_origins(),
        protected_path_prefixes=_csrf_protected_prefixes(),
    )


def configure_cors(app: FastAPI) -> None:
    """Execute configure cors."""
    origins, origin_regex = _cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
