from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_claim_invite_with_principal_skips_commit_when_no_changes(monkeypatch):
    now = datetime.now(UTC)
    db = _DummyDB()
    candidate_session = SimpleNamespace(status="in_progress", started_at=now)

    async def _fake_fetch(_db, _token, *, now):
        return candidate_session

    monkeypatch.setattr(claims_service, "fetch_by_token_for_update", _fake_fetch)
    monkeypatch.setattr(
        claims_service, "ensure_candidate_ownership", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        claims_service, "mark_in_progress", lambda *_args, **_kwargs: None
    )

    loaded = await claims_service.claim_invite_with_principal(
        db,
        "token",
        SimpleNamespace(),
        now=now,
    )

    assert loaded is candidate_session
    assert db.commits == 0
    assert db.refreshes == 0
