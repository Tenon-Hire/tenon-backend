from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_rejects_completed_when_created(monkeypatch):
    cs = CandidateSession(
        trial_id=1,
        candidate_name="Done",
        invite_email="done@test.com",
        token="tok",
        status=CANDIDATE_SESSION_STATUS_COMPLETED,
    )

    async def fake_get_for_update(db, trial_id, invite_email):
        return None

    async def fake_create_invite(db, trial_id, payload, now=None):
        return cs, False

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_trial_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    with pytest.raises(sim_service.InviteRejectedError):
        await sim_service.create_or_resend_invite(
            db=None,
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="done@test.com"),
            now=datetime.now(UTC),
        )
