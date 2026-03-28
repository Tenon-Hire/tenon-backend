from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_fetch_owned_session_skips_commit_for_existing_claim_no_updates(
    monkeypatch,
):
    now = datetime.now(UTC)
    db = _DummyDB()
    candidate_session = SimpleNamespace(candidate_auth0_sub="auth0|already")

    async def _get_by_id(_db, _session_id):
        return candidate_session

    monkeypatch.setattr(fetch_owned_service.cs_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        fetch_owned_service, "ensure_can_access", lambda cs, *_args, **_kwargs: cs
    )
    monkeypatch.setattr(
        fetch_owned_service,
        "ensure_candidate_ownership",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        fetch_owned_service, "apply_auth_updates", lambda *_args, **_kwargs: False
    )

    loaded = await fetch_owned_service.fetch_owned_session(
        db,
        session_id=1,
        principal=SimpleNamespace(),
        now=now,
    )

    assert loaded is candidate_session
    assert db.commits == 0
    assert db.refreshes == 0
