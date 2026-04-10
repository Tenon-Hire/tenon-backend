from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_sends_email_and_tracks_status(
    async_client, async_session, auth_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(async_session, email="notify@app.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")

    with override_dependencies({get_email_service: lambda: email_service}):
        res = await async_client.post(
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
        )

    assert res.status_code == 200, res.text

    cs = (await async_session.execute(select(CandidateSession))).scalar_one()
    assert cs.invite_email_status == "sent"
    assert cs.invite_email_sent_at is not None
    assert len(provider.sent) == 1
    assert provider.sent[0].to == cs.invite_email

    list_res = await async_client.get(
        f"/api/trials/{sim.id}/candidates",
        headers=auth_header_factory(talent_partner),
    )
    assert list_res.status_code == 200
    body = list_res.json()[0]
    assert body["inviteEmailStatus"] == "sent"
    assert body["inviteEmailSentAt"] is not None
