from types import SimpleNamespace

import pytest

from app.shared.auth import rate_limit
from app.shared.http.routes import simulations
from app.simulations import services as sim_service


def _fake_request():
    return type(
        "Req", (), {"headers": {}, "client": type("c", (), {"host": "127.0.0.1"})()}
    )()


class FakeDB:
    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_create_candidate_invite_skips_non_code_tasks(monkeypatch):
    monkeypatch.setattr(rate_limit, "rate_limit_enabled", lambda: False)
    calls = []

    async def fake_require(db, simulation_id, user_id):
        sim = SimpleNamespace(id=1, title="t", role="r", status="active_inviting")
        tasks = [
            SimpleNamespace(id=1, day_index=1, type="design", template_repo=None),
            SimpleNamespace(id=2, day_index=2, type="design", template_repo=None),
        ]
        return sim, tasks

    async def fake_lock(db, simulation_id, now):
        return SimpleNamespace(id=11)

    async def fake_create(db, simulation_id, payload, now, scenario_version_id=None):
        return SimpleNamespace(id=10, token="tok", simulation_id=1), "created"

    async def ensure_workspace(**_kwargs):
        calls.append("workspace")

    async def fake_email(*_args, **_kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        sim_service, "require_owned_simulation_with_tasks", fake_require
    )
    monkeypatch.setattr(sim_service, "lock_active_scenario_for_invites", fake_lock)
    monkeypatch.setattr(sim_service, "create_or_resend_invite", fake_create)
    monkeypatch.setattr(
        simulations.submission_service, "ensure_workspace", ensure_workspace
    )
    monkeypatch.setattr(
        simulations.notification_service, "send_invite_email", fake_email
    )
    resp = await simulations.create_candidate_invite(
        simulation_id=1,
        payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="C"),
        request=_fake_request(),
        db=FakeDB(),
        user=SimpleNamespace(id=1, role="recruiter"),
        email_service=None,
        github_client=None,
    )
    assert resp.candidateSessionId == 10
    assert calls == []
