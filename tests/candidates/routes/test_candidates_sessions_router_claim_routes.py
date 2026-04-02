from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.ai import build_ai_policy_snapshot
from app.shared.http.routes import candidate_sessions
from tests.candidates.routes.test_candidates_sessions_router_routes import (
    StubSession,
    _principal,
    _request,
)


@pytest.mark.asyncio
async def test_claim_route_uses_claim_service(monkeypatch):
    stub_db = StubSession()
    expires_at = datetime.now(UTC)
    simulation = SimpleNamespace(
        id=10,
        title="Sim",
        role="Backend",
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    cs = SimpleNamespace(
        id=3,
        status="in_progress",
        claimed_at=expires_at,
        completed_at=None,
        started_at=expires_at,
        candidate_name="Jane",
        simulation=simulation,
        scenario_version=SimpleNamespace(
            ai_policy_snapshot_json=build_ai_policy_snapshot(simulation=simulation)
        ),
    )

    async def _verify(db, token, principal, now):
        assert token == "t" * 24
        assert principal.email == "test@example.com"
        assert isinstance(now, datetime)
        return cs

    monkeypatch.setattr(
        candidate_sessions.cs_service, "claim_invite_with_principal", _verify
    )
    resp = await candidate_sessions.claim_candidate_session(
        token="t" * 24,
        request=_request(),
        db=stub_db,
        principal=_principal("test@example.com"),
    )

    assert resp.candidateSessionId == cs.id
    assert resp.startedAt == cs.started_at
    assert resp.candidateName == cs.candidate_name
