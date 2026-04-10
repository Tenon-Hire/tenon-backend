from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_refreshes_new_expired(monkeypatch):
    cs = CandidateSession(
        trial_id=1,
        candidate_name="Soon",
        invite_email="soon@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    async def fake_get_for_update(db, trial_id, invite_email):
        return None

    async def fake_create_invite(db, trial_id, payload, now=None):
        return cs, False

    class DummyDB:
        def __init__(self):
            self.commits = 0

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def refresh(self, obj):
            self.refreshed = obj

        async def flush(self):
            return None

    db = DummyDB()
    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_trial_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    refreshed, outcome = await sim_service.create_or_resend_invite(
        db=db,
        trial_id=1,
        payload=SimpleNamespace(inviteEmail="soon@test.com"),
        now=datetime.now(UTC),
    )
    assert refreshed is cs
    assert outcome == "created"
    assert db.commits == 0
