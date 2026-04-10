from types import SimpleNamespace

import pytest

from app.integrations.github.client import GithubError
from app.shared.auth import rate_limit
from app.shared.http import shared_http_error_utils as error_utils
from app.shared.http.routes import trials
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)


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
async def test_create_candidate_invite_rejected(monkeypatch):
    monkeypatch.setattr(rate_limit, "rate_limit_enabled", lambda: False)

    async def fake_require(db, trial_id, user_id):
        return (
            SimpleNamespace(id=1, title="t", role="r", status="active_inviting"),
            [],
        )

    async def fake_lock(db, trial_id, now):
        return SimpleNamespace(id=99)

    async def fake_create(db, trial_id, payload, now, scenario_version_id=None):
        raise sim_service.InviteRejectedError()

    monkeypatch.setattr(sim_service, "require_owned_trial_with_tasks", fake_require)
    monkeypatch.setattr(sim_service, "lock_active_scenario_for_invites", fake_lock)
    monkeypatch.setattr(sim_service, "create_or_resend_invite", fake_create)
    response = await trials.create_candidate_invite(
        trial_id=1,
        payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="C"),
        request=_fake_request(),
        db=FakeDB(),
        user=SimpleNamespace(id=1, role="talent_partner"),
        email_service=None,
        github_client=None,
    )
    assert response.status_code == 409
    assert response.body


@pytest.mark.asyncio
async def test_create_candidate_invite_github_error(monkeypatch):
    monkeypatch.setattr(rate_limit, "rate_limit_enabled", lambda: False)
    task = SimpleNamespace(id=2, day_index=2, type="code", template_repo="owner/repo")

    async def _ensure_bundle(*_args, **_kwargs):
        return None

    async def fake_require(db, trial_id, user_id):
        return SimpleNamespace(id=1, title="t", role="r", status="active_inviting"), [
            task
        ]

    async def fake_lock(db, trial_id, now):
        return SimpleNamespace(id=11, template_key="python-fastapi")

    async def fake_create(db, trial_id, payload, now, scenario_version_id=None):
        return SimpleNamespace(id=10, token="tok"), "created"

    async def fail_workspace(_db, **_kwargs):
        raise GithubError("nope", status_code=403)

    monkeypatch.setattr(sim_service, "require_owned_trial_with_tasks", fake_require)
    monkeypatch.setattr(sim_service, "lock_active_scenario_for_invites", fake_lock)
    monkeypatch.setattr(sim_service, "create_or_resend_invite", fake_create)
    monkeypatch.setattr(trials.submission_service, "ensure_workspace", fail_workspace)
    monkeypatch.setattr(
        invite_workflow.codespace_specializer,
        "ensure_precommit_bundle_ready_for_invites",
        _ensure_bundle,
    )
    with pytest.raises(error_utils.ApiError) as excinfo:
        await trials.create_candidate_invite(
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="C"),
            request=_fake_request(),
            db=FakeDB(),
            user=SimpleNamespace(id=1, role="talent_partner"),
            email_service=None,
            github_client=None,
        )
    assert excinfo.value.error_code == "GITHUB_PERMISSION_DENIED"
