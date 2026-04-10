from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_record_candidate_session_consent_rejects_blank_notice(async_session):
    talent_partner = await create_talent_partner(
        async_session,
        email="privacy-consent-invalid@test.com",
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

    with pytest.raises(HTTPException) as exc_info:
        await record_candidate_session_consent(
            async_session,
            candidate_session=candidate_session,
            notice_version="   ",
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "noticeVersion is required"
