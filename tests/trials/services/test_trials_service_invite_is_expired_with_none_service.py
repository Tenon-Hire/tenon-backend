from __future__ import annotations

from tests.trials.services.trials_core_service_utils import *


def test_invite_is_expired_with_none():
    cs = SimpleNamespace(expires_at=None)
    assert sim_service._invite_is_expired(cs, now=datetime.now(UTC)) is False
