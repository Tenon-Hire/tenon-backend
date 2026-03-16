from __future__ import annotations

from fastapi import FastAPI

from app.api.routers import (
    admin_routes,
    admin_templates,
    auth,
    candidate_sessions,
    fit_profile,
    github_webhooks,
    health,
    jobs,
    recordings,
    simulations,
    submissions,
    tasks_codespaces,
)
from app.core.settings import settings


def register_routers(app: FastAPI) -> None:
    prefix = settings.API_PREFIX
    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(jobs.router, prefix=f"{prefix}", tags=["jobs"])
    app.include_router(admin_templates.router, prefix=f"{prefix}/admin", tags=["admin"])
    app.include_router(admin_routes.router, prefix=f"{prefix}/admin", tags=["admin"])
    app.include_router(simulations.router, prefix=f"{prefix}", tags=["simulations"])
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
    app.include_router(fit_profile.router, prefix=f"{prefix}", tags=["fit_profile"])


__all__ = ["register_routers"]
