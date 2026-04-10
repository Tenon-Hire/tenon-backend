from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.trials.services import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)


@pytest.mark.asyncio
async def test_invite_workflow_re_raises_unrelated_typeerror_from_require(monkeypatch):
    async def _raise_typeerror(*_args, **_kwargs):
        raise TypeError("unexpected signature mismatch")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _raise_typeerror,
    )

    with pytest.raises(TypeError, match="unexpected signature mismatch"):
        await invite_workflow.create_candidate_invite_workflow(
            db=object(),
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="Name"),
            user_id=2,
            email_service=object(),
            github_client=object(),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_invite_workflow_re_raises_unrelated_typeerror_from_lock(monkeypatch):
    async def _require_owned(*_args, **_kwargs):
        return SimpleNamespace(id=1, token="tok"), []

    async def _raise_typeerror(*_args, **_kwargs):
        raise TypeError("lock call failed")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_trial_invitable",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "lock_active_scenario_for_invites",
        _raise_typeerror,
    )

    with pytest.raises(TypeError, match="lock call failed"):
        await invite_workflow.create_candidate_invite_workflow(
            db=object(),
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="Name"),
            user_id=2,
            email_service=object(),
            github_client=object(),
            now=datetime.now(UTC),
        )
