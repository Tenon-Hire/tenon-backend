from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_resolve_create_invite_callable_falls_back_when_service_callable_missing(
    monkeypatch,
):
    from app.simulations import services as simulations_service
    from app.simulations.services.simulations_services_simulations_invite_create_service import (
        create_invite,
    )

    monkeypatch.setattr(simulations_service, "create_invite", None, raising=False)

    resolved = invite_factory.resolve_create_invite_callable()

    assert resolved is create_invite
