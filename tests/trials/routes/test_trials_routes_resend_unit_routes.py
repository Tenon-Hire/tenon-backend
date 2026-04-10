from types import SimpleNamespace

import pytest

from app.shared.auth import rate_limit
from app.shared.http.routes import trials
from app.trials import services as sim_service


def _fake_request():
    return type(
        "Req", (), {"headers": {}, "client": type("c", (), {"host": "127.0.0.1"})()}
    )()


@pytest.mark.asyncio
async def test_resend_candidate_invite_rate_limited(monkeypatch):
    monkeypatch.setattr(rate_limit, "rate_limit_enabled", lambda: True)
    limiter_calls = []

    class DummyLimiter:
        def allow(self, key, rule):
            limiter_calls.append(key)

    monkeypatch.setattr(rate_limit, "limiter", DummyLimiter())

    async def fake_require(db, trial_id, user_id):
        return SimpleNamespace(id=1, status="active_inviting")

    fake_cs = SimpleNamespace(
        id=2,
        trial_id=1,
        token="tok",
        invite_email_status=None,
        invite_email_sent_at=None,
        invite_email_error=None,
    )

    class FakeSession:
        async def get(self, model, id):
            return fake_cs

    async def fake_send(db, candidate_session, trial, invite_url, email_service, now):
        fake_cs.invite_email_status = "sent"
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(sim_service, "require_owned_trial", fake_require)
    monkeypatch.setattr(trials.notification_service, "send_invite_email", fake_send)
    result = await trials.resend_candidate_invite(
        trial_id=1,
        candidate_session_id=2,
        request=_fake_request(),
        db=FakeSession(),
        user=SimpleNamespace(id=1, role="talent_partner"),
        email_service=None,
    )
    assert result["inviteEmailStatus"] == "sent"
    assert limiter_calls


@pytest.mark.asyncio
async def test_resend_candidate_invite_not_found(monkeypatch):
    monkeypatch.setattr(rate_limit, "rate_limit_enabled", lambda: False)

    async def fake_require(db, trial_id, user_id):
        return SimpleNamespace(id=1, status="active_inviting")

    class FakeSession:
        async def get(self, model, id):
            return SimpleNamespace(trial_id=999)

    monkeypatch.setattr(sim_service, "require_owned_trial", fake_require)
    with pytest.raises(Exception) as excinfo:
        await trials.resend_candidate_invite(
            trial_id=1,
            candidate_session_id=2,
            request=_fake_request(),
            db=FakeSession(),
            user=SimpleNamespace(id=1, role="talent_partner"),
            email_service=None,
        )
    assert excinfo.value.status_code == 404
