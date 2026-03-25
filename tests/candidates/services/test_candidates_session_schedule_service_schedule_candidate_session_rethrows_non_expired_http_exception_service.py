from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


@pytest.mark.asyncio
async def test_schedule_candidate_session_rethrows_non_expired_http_exception(
    async_session, monkeypatch
):
    principal = _principal(
        "invalid-token@test.com",
        sub="candidate-invalid-token@test.com",
        email_verified=True,
    )
    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")

    async def _raise_not_found(*_args, **_kwargs):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token"
        )

    monkeypatch.setattr(
        schedule_service,
        "fetch_by_token_for_update",
        _raise_not_found,
    )

    with pytest.raises(HTTPException) as excinfo:
        await schedule_service.schedule_candidate_session(
            async_session,
            token="x" * 24,
            principal=principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"
