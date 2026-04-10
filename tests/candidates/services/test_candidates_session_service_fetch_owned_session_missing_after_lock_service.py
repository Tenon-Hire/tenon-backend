from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_missing_after_lock(monkeypatch):
    principal = _principal("lock@test.com")
    cs_stub = type(
        "CS",
        (),
        {
            "id": 1,
            "trial_id": 1,
            "candidate_auth0_sub": None,
            "candidate_email": "lock@test.com",
            "invite_email": "lock@test.com",
            "expires_at": None,
            "status": "not_started",
        },
    )()

    async def fake_get_by_id(db, session_id):
        return cs_stub

    async def fake_get_by_id_for_update(db, session_id):
        return None

    monkeypatch.setattr(cs_service.cs_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(
        cs_service.cs_repo, "get_by_id_for_update", fake_get_by_id_for_update
    )
    dummy_db = _DummyDB(None)
    with pytest.raises(HTTPException) as excinfo:
        await cs_service.fetch_owned_session(
            dummy_db, 1, principal, now=datetime.now(UTC)
        )
    assert excinfo.value.status_code == 404
