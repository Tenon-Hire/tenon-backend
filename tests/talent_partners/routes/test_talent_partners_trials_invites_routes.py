from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.http.routes import trials as talent_partner_sims
from app.trials.services import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)


def _request(host: str = "127.0.0.1"):
    return SimpleNamespace(headers={}, client=SimpleNamespace(host=host))


class FakeDB:
    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_create_candidate_invite_happy_path(monkeypatch):
    user = SimpleNamespace(id=1)
    cs = SimpleNamespace(id=2, token="tok")
    task_day2 = SimpleNamespace(
        id=10, day_index=2, type="code", template_repo="org/template"
    )
    task_day3 = SimpleNamespace(
        id=11, day_index=3, type="code", template_repo="org/template"
    )

    async def _require_owned_with_tasks(db, trial_id, talent_partner_id):
        assert talent_partner_id == user.id
        return (
            SimpleNamespace(
                id=trial_id, title="Sim", role="Engineer", status="active_inviting"
            ),
            [task_day2, task_day3],
        )

    async def _lock_active_scenario_for_invites(db, trial_id, now):
        return SimpleNamespace(id=777, template_key="python-fastapi")

    async def _create_or_resend_invite(
        db, trial_id, payload, now, scenario_version_id=None
    ):
        assert payload.candidateName == "Name"
        return cs, "created"

    async def _send_invite_email(*_args, **_kwargs):
        return SimpleNamespace(status="sent")

    async def _ensure_workspace(*_args, **_kwargs):
        return SimpleNamespace(id="ws")

    monkeypatch.setattr(
        talent_partner_sims, "ensure_talent_partner_or_none", lambda _u: None
    )
    monkeypatch.setattr(
        talent_partner_sims.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned_with_tasks,
    )
    monkeypatch.setattr(
        talent_partner_sims.sim_service,
        "lock_active_scenario_for_invites",
        _lock_active_scenario_for_invites,
    )
    monkeypatch.setattr(
        talent_partner_sims.sim_service,
        "create_or_resend_invite",
        _create_or_resend_invite,
    )
    monkeypatch.setattr(
        talent_partner_sims.notification_service,
        "send_invite_email",
        _send_invite_email,
    )
    monkeypatch.setattr(
        talent_partner_sims.submission_service, "ensure_workspace", _ensure_workspace
    )
    monkeypatch.setattr(
        talent_partner_sims.sim_service,
        "invite_url",
        lambda token: f"https://portal/{token}",
    )

    resp = await talent_partner_sims.create_candidate_invite(
        trial_id=5,
        payload=SimpleNamespace(candidateName="Name", inviteEmail="a@b.com"),
        request=_request(),
        db=FakeDB(),
        user=user,
        email_service=SimpleNamespace(
            send_email=lambda **_k: SimpleNamespace(status="sent")
        ),
        github_client=SimpleNamespace(),
    )
    assert resp.inviteUrl.endswith("/tok")
    assert resp.candidateSessionId == cs.id
    assert resp.outcome == "created"
