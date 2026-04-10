"""Application module for http builder service workflows."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.shared.http.errors.shared_http_errors_handlers_utils import (
    register_error_handlers,
)
from app.shared.http.shared_http_app_meta_service import _env_name
from app.shared.http.shared_http_lifespan_service import lifespan
from app.shared.http.shared_http_middleware import (
    configure_core_logging,
    configure_cors,
    configure_csrf_protection,
    configure_perf_logging,
    configure_proxy_headers,
    configure_request_limits,
)
from app.shared.http.shared_http_router_registry_service import register_routers
from app.shared.utils.shared_utils_brand_utils import APP_NAME


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    configure_core_logging()
    if settings.dev_auth_bypass_enabled and _env_name() != "local":
        raise RuntimeError(
            "Refusing to start: DEV_AUTH_BYPASS/WINOE_DEV_AUTH_BYPASS enabled "
            "outside WINOE_ENV=local"
        )

    app = FastAPI(title=f"{APP_NAME} Backend", version="0.1.0", lifespan=lifespan)
    configure_perf_logging(app)
    configure_proxy_headers(app)
    configure_request_limits(app)
    configure_csrf_protection(app)
    configure_cors(app)
    register_routers(app)
    register_error_handlers(app)
    return app


__all__ = ["create_app"]
