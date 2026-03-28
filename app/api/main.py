"""Expose the FastAPI application instance and API-entrypoint helpers."""

from app.config import settings
from app.shared.database import init_db_if_needed
from app.shared.http.shared_http_app_builder_service import create_app
from app.shared.http.shared_http_app_meta_service import _env_name, _parse_csv
from app.shared.http.shared_http_lifespan_service import lifespan
from app.shared.http.shared_http_middleware_http_middleware import (
    _cors_config as _resolved_cors_config,
)
from app.shared.perf import perf_logging_enabled

app = create_app()


def _cors_config() -> tuple[list[str], str | None]:
    """Return effective CORS origin settings after environment normalization."""
    return _resolved_cors_config()


def _configure_perf_logging(app) -> None:
    """Attach SQL/per-request perf middleware when perf logging is enabled."""
    if not perf_logging_enabled():
        return
    from app.shared.utils import shared_utils_db_utils as db
    from app.shared.utils import shared_utils_perf_utils as perf

    perf.attach_sqlalchemy_listeners(db.engine)
    app.add_middleware(perf.RequestPerfMiddleware)


__all__ = [
    "app",
    "create_app",
    "lifespan",
    "_parse_csv",
    "_env_name",
    "_cors_config",
    "_configure_perf_logging",
    "perf_logging_enabled",
    "settings",
    "init_db_if_needed",
]
