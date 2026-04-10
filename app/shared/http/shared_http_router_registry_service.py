"""Application module for http router registry service workflows."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.shared.auth.shared_auth_admin_api_key_utils import is_admin_key_configured
from app.shared.http.routes import (
    admin_routes,
    admin_templates,
    candidate_sessions,
    github_webhooks,
    recordings,
    submissions,
    tasks_codespaces,
    trials,
    winoe_report,
)
from app.shared.http.routes import shared_http_routes_auth_routes as auth
from app.shared.http.routes import (
    shared_http_routes_companies_routes as companies,
)
from app.shared.http.routes import shared_http_routes_health_routes as health
from app.shared.http.routes import shared_http_routes_jobs_routes as jobs


def register_routers(app: FastAPI) -> None:
    """Execute register routers."""
    prefix = settings.API_PREFIX
    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(companies.router, prefix=f"{prefix}", tags=["companies"])
    app.include_router(jobs.router, prefix=f"{prefix}", tags=["jobs"])
    app.include_router(admin_templates.router, prefix=f"{prefix}/admin", tags=["admin"])
    app.include_router(admin_routes.router, prefix=f"{prefix}/admin", tags=["admin"])
    if is_admin_key_configured():
        app.include_router(
            admin_routes.dev_session_controls.router,
            prefix=f"{prefix}/admin",
            tags=["admin"],
        )
    app.include_router(trials.router, prefix=f"{prefix}", tags=["trials"])
    app.include_router(
        candidate_sessions.router, prefix=f"{prefix}/candidate", tags=["candidate"]
    )
    app.include_router(
        tasks_codespaces.router, prefix=f"{prefix}/tasks", tags=["tasks"]
    )
    app.include_router(
        github_webhooks.router,
        prefix=f"{prefix}",
        tags=["integration", "github"],
    )
    app.include_router(recordings.router, prefix=f"{prefix}", tags=["recordings"])
    app.include_router(submissions.router, prefix=f"{prefix}")
    app.include_router(winoe_report.router, prefix=f"{prefix}", tags=["winoe_report"])


__all__ = ["register_routers"]
