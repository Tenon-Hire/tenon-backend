"""Application module for submissions routes submissions helpers guard routes workflows."""

from __future__ import annotations

from app.shared.auth.shared_auth_roles_utils import ensure_recruiter


def ensure_recruiter_guard(user):
    """Ensure recruiter guard."""
    try:
        from app.shared.http.routes import submissions as submissions_routes
    except Exception:
        return ensure_recruiter(user)
    return getattr(submissions_routes, "ensure_recruiter", ensure_recruiter)(user)


__all__ = ["ensure_recruiter_guard"]
