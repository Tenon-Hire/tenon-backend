from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_refresh_invite_token_retries_on_integrity(monkeypatch):
    class DummyDB:
        def __init__(self):
            self.calls = 0

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            self.calls += 1
            if self.calls == 1:
                raise IntegrityError("", "", "")

    cs = CandidateSession(
        trial_id=1,
        candidate_name="Retry",
        invite_email="retry@test.com",
        token="tok",
        status="not_started",
    )
    db = DummyDB()
    refreshed = await sim_service._refresh_invite_token(db, cs, now=datetime.now(UTC))
    assert refreshed.token != "tok"
    assert db.calls == 2
