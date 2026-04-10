from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_invite_handles_token_collisions(monkeypatch):
    class StubSession:
        def __init__(self):
            self.flushes = 0
            self.added: CandidateSession | None = None

        def add(self, obj):
            self.added = obj

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            self.flushes += 1
            raise IntegrityError("", {}, None)

        async def execute(self, *_args, **_kwargs):
            class _Result:
                def scalar_one_or_none(self):
                    return None

            return _Result()

    with pytest.raises(Exception) as excinfo:
        await sim_service.create_invite(
            StubSession(),
            trial_id=1,
            payload=type("P", (), {"candidateName": "x", "inviteEmail": "y"}),
        )
    assert excinfo.value.status_code == 500
