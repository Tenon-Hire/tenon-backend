from app.api.app_builder import create_app
from app.api.app_meta import _env_name, _parse_csv
from app.api.lifespan import lifespan
from app.api.middleware_http import _cors_config as _resolved_cors_config
from app.core.db import init_db_if_needed
from app.core.perf import perf_logging_enabled
from app.core.settings import settings

app = create_app()


def _cors_config() -> tuple[list[str], str | None]:
    return _resolved_cors_config()


def _configure_perf_logging(app) -> None:
    if not perf_logging_enabled():
        return
    from app.core import db, perf

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
