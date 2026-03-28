"""Application module for http lifespan service workflows."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.database import init_db_if_needed as _init_db_if_needed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """FastAPI lifespan handler to run startup/shutdown tasks."""
    from app.api import main as api_main

    await getattr(api_main, "init_db_if_needed", _init_db_if_needed)()
    try:
        yield
    finally:
        try:
            from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
                _github_client_singleton,
            )

            client = _github_client_singleton()
            await client.aclose()
        except Exception:
            # Best-effort cleanup; swallow errors to avoid blocking shutdown.
            pass


__all__ = ["lifespan"]
