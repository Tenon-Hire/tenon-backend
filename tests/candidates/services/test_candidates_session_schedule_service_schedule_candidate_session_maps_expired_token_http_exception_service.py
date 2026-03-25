from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_maps_expired_token_http_exception(
    async_session, monkeypatch
):
    principal = _principal(
        "expired-token@test.com",
        sub="candidate-expired-token@test.com",
        email_verified=True,
    )
    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")

    async def _raise_expired(*_args, **_kwargs):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Invite token expired"
        )

    monkeypatch.setattr(
        schedule_service,
        "fetch_by_token_for_update",
        _raise_expired,
    )

    with pytest.raises(ApiError) as excinfo:
        await schedule_service.schedule_candidate_session(
            async_session,
            token="x" * 24,
            principal=principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert excinfo.value.status_code == status.HTTP_410_GONE
    assert excinfo.value.error_code == "INVITE_TOKEN_EXPIRED"
