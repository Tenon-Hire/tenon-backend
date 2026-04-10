from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_record_candidate_session_consent_logs_audit_safe_event(
    async_session,
    caplog,
):
    caplog.set_level(
        "INFO", logger="app.media.services.media_services_media_privacy_service"
    )
    talent_partner = await create_talent_partner(
        async_session, email="privacy-consent-log@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="consent-log-candidate@test.com",
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    await record_candidate_session_consent(
        async_session,
        candidate_session=candidate_session,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert (
        f"consent recorded candidateSessionId={candidate_session.id} consentVersion=mvp1"
        in log_text
    )
    assert candidate_session.invite_email not in log_text
    assert "https://" not in log_text
    assert "Bearer " not in log_text
