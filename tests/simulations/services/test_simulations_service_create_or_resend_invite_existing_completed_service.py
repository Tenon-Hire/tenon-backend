from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_existing_completed(monkeypatch):
    existing = CandidateSession(
        simulation_id=1,
        candidate_name="Done",
        invite_email="done@test.com",
        token="tok",
        status=CANDIDATE_SESSION_STATUS_COMPLETED,
    )

    async def fake_get_for_update(db, simulation_id, invite_email):
        return existing

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_simulation_and_email_for_update",
        fake_get_for_update,
    )
    with pytest.raises(sim_service.InviteRejectedError):
        await sim_service.create_or_resend_invite(
            db=None,
            simulation_id=1,
            payload=SimpleNamespace(inviteEmail="done@test.com"),
            now=datetime.now(UTC),
        )
