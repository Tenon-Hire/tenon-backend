from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.routers.candidate_sessions_routes import privacy as privacy_route
from app.core.auth.principal import Principal
from app.schemas.candidate_sessions import CandidatePrivacyConsentRequest


def _principal(email: str = "candidate@test.com") -> Principal:
    return Principal(
        sub=f"candidate-{email}",
        email=email,
        name="candidate",
        roles=[],
        permissions=["candidate:access"],
        claims={"email_verified": True},
    )


@pytest.mark.asyncio
async def test_record_candidate_privacy_consent_route(monkeypatch):
    captured = {}

    async def _fetch_owned_session(db, candidate_session_id: int, principal, *, now):
        del db, principal, now
        return SimpleNamespace(id=candidate_session_id)

    async def _record_consent(
        db,
        *,
        candidate_session,
        notice_version: str,
        ai_notice_version: str | None,
    ):
        del db
        captured["session_id"] = candidate_session.id
        captured["notice_version"] = notice_version
        captured["ai_notice_version"] = ai_notice_version
        return candidate_session

    monkeypatch.setattr(
        privacy_route.cs_service, "fetch_owned_session", _fetch_owned_session
    )
    monkeypatch.setattr(
        privacy_route,
        "record_candidate_session_consent",
        _record_consent,
    )

    response = await privacy_route.record_candidate_privacy_consent(
        candidate_session_id=17,
        payload=CandidatePrivacyConsentRequest(noticeVersion="mvp1"),
        principal=_principal(),
        db=None,
    )

    assert response.status == "consent_recorded"
    assert captured == {
        "session_id": 17,
        "notice_version": "mvp1",
        "ai_notice_version": None,
    }
