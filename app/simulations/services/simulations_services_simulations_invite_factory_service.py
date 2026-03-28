"""Application module for simulations services simulations invite factory service workflows."""

from __future__ import annotations


def resolve_create_invite_callable():
    """Resolve create invite callable."""
    try:
        from app.simulations import services as sim_service

        if getattr(sim_service, "create_invite", None):
            return sim_service.create_invite
    except Exception:
        pass
    from .simulations_services_simulations_invite_create_service import create_invite

    return create_invite
