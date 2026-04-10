from __future__ import annotations

import pytest

from tests.media.routes.media_privacy_api_utils import *


@pytest.mark.asyncio
async def test_candidate_privacy_consent_endpoint_records_fields(
    async_client,
    async_session,
    candidate_header_factory,
):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-consent-api@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/candidate/session/{candidate_session.id}/privacy/consent",
        headers=candidate_header_factory(candidate_session),
        json={"noticeVersion": "mvp1"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "consent_recorded"}

    refreshed = await async_session.get(CandidateSession, candidate_session.id)
    assert refreshed is not None
    assert refreshed.consent_version == "mvp1"
    assert refreshed.consent_timestamp is not None
    assert refreshed.ai_notice_version == "mvp1"
