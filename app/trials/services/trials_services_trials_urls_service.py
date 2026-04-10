"""Application module for trials services trials urls service workflows."""

from __future__ import annotations

from app.config import settings


def invite_url(token: str) -> str:
    """Construct candidate portal URL for an invite token."""
    return f"{settings.CANDIDATE_PORTAL_BASE_URL.rstrip('/')}/candidate/session/{token}"
