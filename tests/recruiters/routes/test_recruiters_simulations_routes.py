from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.shared.http.routes import simulations as recruiter_sims


@pytest.mark.asyncio
async def test_list_simulation_candidates_calls_service(monkeypatch):
    user = SimpleNamespace(id=7)
    cs = SimpleNamespace(
        id=11,
        invite_email="x@y.com",
        candidate_name="Jane",
        status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    monkeypatch.setattr(recruiter_sims, "ensure_recruiter_or_none", lambda _u: None)

    async def _require_owned(*_a, **_k):
        return cs

    async def _list_candidates(*_a, **_k):
        return [(cs, None)]

    monkeypatch.setattr(
        recruiter_sims.sim_service, "require_owned_simulation", _require_owned
    )
    monkeypatch.setattr(
        recruiter_sims.sim_service, "list_candidates_with_profile", _list_candidates
    )
    resp = await recruiter_sims.list_simulation_candidates(
        simulation_id=9, db=None, user=user
    )
    assert resp[0].candidateSessionId == cs.id
    assert resp[0].hasFitProfile is False
