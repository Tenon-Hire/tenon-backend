from __future__ import annotations

import pytest

from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_headers_accept_missing_candidate_token(monkeypatch, async_session):
    cs = _stub_cs()
    fixed_now = shared_utcnow()
    monkeypatch.setattr(
        "app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.shared_utcnow",
        lambda: fixed_now,
    )

    async def _return_session(db, session_id, principal, now):
        assert session_id == cs.id
        assert now == fixed_now
        return cs

    monkeypatch.setattr(
        "app.shared.http.dependencies.candidate_sessions.cs_service.fetch_owned_session",
        _return_session,
    )

    result = await candidate_session_from_headers(
        principal=_principal(),
        x_candidate_session_id=cs.id,
        db=async_session,
    )
    assert result == cs
