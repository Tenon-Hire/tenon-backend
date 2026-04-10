from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_resolve_create_invite_callable_falls_back_when_service_callable_missing(
    monkeypatch,
):
    from app.trials import services as trials_service
    from app.trials.services.trials_services_trials_invite_create_service import (
        create_invite,
    )

    monkeypatch.setattr(trials_service, "create_invite", None, raising=False)

    resolved = invite_factory.resolve_create_invite_callable()

    assert resolved is create_invite
