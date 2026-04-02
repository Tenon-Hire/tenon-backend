from app.candidates.routes import candidate_sessions
from app.evaluations.routes import (
    evaluations_routes_evaluations_fit_profile_routes as fit_profile,
)
from app.media.routes import media_routes_media_recordings_routes as recordings
from app.recruiters.routes import admin_routes, admin_templates
from app.simulations.routes import simulations
from app.submissions.routes import github_webhooks, submissions, submissions_helpers
from app.submissions.routes import (
    submissions_routes_submissions_helpers_guard_routes as submissions_helpers_guard,
)
from app.tasks.routes import (
    tasks_routes_tasks_codespaces_routes as tasks_codespaces_routes,
)

from . import (
    shared_http_routes_auth_routes,
    shared_http_routes_companies_routes,
    shared_http_routes_health_routes,
    shared_http_routes_jobs_routes,
)

# Temporary alias while route-import call sites migrate.
tasks_codespaces = tasks_codespaces_routes

__all__ = [
    "admin_routes",
    "admin_templates",
    "shared_http_routes_auth_routes",
    "shared_http_routes_companies_routes",
    "candidate_sessions",
    "fit_profile",
    "github_webhooks",
    "shared_http_routes_health_routes",
    "shared_http_routes_jobs_routes",
    "recordings",
    "simulations",
    "submissions",
    "submissions_helpers",
    "submissions_helpers_guard",
    "tasks_codespaces",
    "tasks_codespaces_routes",
]
