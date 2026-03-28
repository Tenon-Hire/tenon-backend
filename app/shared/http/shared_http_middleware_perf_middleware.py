"""Application module for http middleware perf middleware workflows."""

from __future__ import annotations

from fastapi import FastAPI

from app.shared.logging import configure_logging
from app.shared.perf import RequestPerfMiddleware, perf_logging_enabled


def configure_core_logging() -> None:
    """Execute configure core logging."""
    configure_logging()


def configure_perf_logging(app: FastAPI) -> None:
    """Execute configure perf logging."""
    if not perf_logging_enabled():
        return
    from app.shared.database import engine
    from app.shared.perf import attach_sqlalchemy_listeners

    attach_sqlalchemy_listeners(engine)
    app.add_middleware(RequestPerfMiddleware)


__all__ = ["configure_core_logging", "configure_perf_logging"]
