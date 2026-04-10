from __future__ import annotations

from tests.trials.services.trials_core_service_utils import *


def test_invite_url_uses_portal_base(monkeypatch):
    monkeypatch.setattr(
        sim_service.settings, "CANDIDATE_PORTAL_BASE_URL", "https://portal.test"
    )
    assert sim_service.invite_url("abc") == "https://portal.test/candidate/session/abc"
