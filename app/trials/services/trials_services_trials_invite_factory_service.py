"""Application module for trials services trials invite factory service workflows."""

from __future__ import annotations


def resolve_create_invite_callable():
    """Resolve create invite callable."""
    try:
        from app.trials import services as trial_service

        if getattr(trial_service, "create_invite", None):
            return trial_service.create_invite
    except Exception:
        pass
    from .trials_services_trials_invite_create_service import create_invite

    return create_invite
