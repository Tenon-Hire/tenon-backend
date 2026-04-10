from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_invite_factory_fallbacks(monkeypatch):
    from app.trials import services as sim_service

    def marker():
        return "from-service"

    monkeypatch.setattr(sim_service, "create_invite", marker)
    assert invite_factory.resolve_create_invite_callable() is marker

    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.trials" and "services" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    resolved = invite_factory.resolve_create_invite_callable()
    from app.trials.services.trials_services_trials_invite_create_service import (
        create_invite,
    )

    assert resolved is create_invite
