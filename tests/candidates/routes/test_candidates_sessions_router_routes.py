from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import settings
from app.shared.auth.principal import Principal
from app.shared.http.routes import candidate_sessions


def _principal(email: str) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    return Principal(
        sub=f"auth0|{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=["candidate:access"],
        claims={
            "sub": f"auth0|{email}",
            "email": email,
            email_claim: email,
            "permissions": ["candidate:access"],
            permissions_claim: ["candidate:access"],
        },
    )


class StubSession:
    def __init__(self):
        self.committed = False
        self.refreshed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, _obj, **_kwargs):
        self.refreshed = True


def _request(host: str = "127.0.0.1", headers: dict | None = None):
    return SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host=host))


@pytest.mark.asyncio
async def test_resolve_candidate_session_propagates_claim_error(monkeypatch):
    stub_db = StubSession()

    async def _claim(*_a, **_k):
        raise HTTPException(status_code=403, detail="Forbidden")

    monkeypatch.setattr(
        candidate_sessions.cs_service, "claim_invite_with_principal", _claim
    )
    with pytest.raises(HTTPException) as excinfo:
        await candidate_sessions.resolve_candidate_session(
            token="t" * 24,
            request=_request(),
            db=stub_db,
            principal=_principal("test@example.com"),
        )
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_task_marks_completed(monkeypatch):
    stub_db = StubSession()
    cs = SimpleNamespace(
        id=2,
        status="in_progress",
        completed_at=None,
        trial_id=1,
    )
    current_task = SimpleNamespace(
        id=99, day_index=3, title="Task", type="code", description="desc"
    )

    async def _fetch_by_id(db, session_id, principal, now):
        assert session_id == cs.id
        return cs

    async def _progress_snapshot(db, candidate_session, **_kwargs):
        return (
            [current_task],
            {1, 2, 3},
            current_task,
            3,
            3,
            True,
        )

    monkeypatch.setattr(
        candidate_sessions.cs_service, "fetch_owned_session", _fetch_by_id
    )
    monkeypatch.setattr(
        candidate_sessions.cs_service,
        "ensure_schedule_started_for_content",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        candidate_sessions.cs_service, "progress_snapshot", _progress_snapshot
    )

    resp = await candidate_sessions.get_current_task(
        candidate_session_id=cs.id,
        request=_request(headers={"x-candidate-session-id": str(cs.id)}),
        db=stub_db,
        principal=_principal("user@example.com"),
    )
    assert resp.isComplete is True
    assert resp.currentDayIndex is None
    assert cs.status == "completed"
    assert stub_db.committed is True
    assert cs.completed_at is not None
