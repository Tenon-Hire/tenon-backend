"""Thin re-exports so deployment entrypoints can import `app` from app.main."""

from app.api.main import (
    _env_name,
    _parse_csv,
    app,
    create_app,
    lifespan,
)

# Explicit re-exports for uvicorn/gunicorn entrypoints and tests.
__all__ = ["app", "create_app", "lifespan", "_parse_csv", "_env_name"]
