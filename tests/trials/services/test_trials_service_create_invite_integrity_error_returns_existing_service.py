from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_invite_integrity_error_returns_existing(monkeypatch):
    existing = CandidateSession(
        trial_id=1,
        candidate_name="Jane",
        invite_email="jane@example.com",
        token="token",
        status="not_started",
        expires_at=datetime.now(UTC),
    )
    existing.id = 123

    class StubSession:
        def add(self, _obj):
            return None

        def begin_nested(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def flush(self):
            raise IntegrityError("", {}, None)

    async def _get_existing(*_args, **_kwargs):
        return existing

    monkeypatch.setattr(sim_service.cs_repo, "get_by_trial_and_email", _get_existing)
    cs, created = await sim_service.create_invite(
        StubSession(),
        trial_id=1,
        payload=type(
            "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
        ),
        now=datetime.now(UTC),
    )
    assert cs.id == existing.id
    assert created is False
