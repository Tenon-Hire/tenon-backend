from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_record_candidate_session_consent_is_idempotent(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="privacy-consent@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    recorded = await record_candidate_session_consent(
        async_session,
        candidate_session=candidate_session,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )
    first_timestamp = recorded.consent_timestamp
    assert recorded.consent_version == "mvp1"
    assert first_timestamp is not None

    recorded_again = await record_candidate_session_consent(
        async_session,
        candidate_session=recorded,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )
    assert recorded_again.consent_timestamp == first_timestamp
