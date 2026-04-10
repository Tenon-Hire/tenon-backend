"""Application module for submissions routes submissions helpers guard routes workflows."""

from __future__ import annotations

from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner


def ensure_talent_partner_guard(user):
    """Ensure Talent Partner guard."""
    try:
        from app.shared.http.routes import submissions as submissions_routes
    except Exception:
        return ensure_talent_partner(user)
    return getattr(submissions_routes, "ensure_talent_partner", ensure_talent_partner)(
        user
    )


__all__ = ["ensure_talent_partner_guard"]
