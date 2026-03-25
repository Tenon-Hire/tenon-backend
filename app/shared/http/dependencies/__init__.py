"""Shared FastAPI dependencies used across routers."""

import app.shared.http.dependencies.shared_http_dependencies_admin_demo_actor_utils as admin_demo_actor
import app.shared.http.dependencies.shared_http_dependencies_admin_demo_rules_utils as admin_demo_rules
import app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils as admin_demo
import app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils as candidate_sessions
import app.shared.http.dependencies.shared_http_dependencies_github_native_utils as github_native
import app.shared.http.dependencies.shared_http_dependencies_notifications_utils as notifications
import app.shared.http.dependencies.shared_http_dependencies_storage_media_utils as storage_media

__all__ = [
    "admin_demo",
    "admin_demo_actor",
    "admin_demo_rules",
    "candidate_sessions",
    "github_native",
    "notifications",
    "storage_media",
]
