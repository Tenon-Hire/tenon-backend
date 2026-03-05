from __future__ import annotations

import re
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.core.auth.principal import Principal
from app.core.errors import ApiError
from app.core.settings import settings
from app.integrations.notifications.email_provider import MemoryEmailProvider
from app.services.candidate_sessions import schedule as schedule_service
from app.services.email import EmailService
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _principal(
    email: str,
    *,
    sub: str | None = None,
    email_verified: bool | None = True,
) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    claims = {
        "sub": sub or f"candidate-{email}",
        "email": email,
        email_claim: email,
        "permissions": ["candidate:access"],
        permissions_claim: ["candidate:access"],
    }
    if email_verified is not None:
        claims["email_verified"] = email_verified
    return Principal(
        sub=sub or f"candidate-{email}",
        email=email,
        name=email.split("@")[0] if email else "",
        roles=[],
        permissions=["candidate:access"],
        claims=claims,
    )


@pytest.mark.asyncio
async def test_schedule_candidate_session_success_idempotent_and_conflict(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="schedule-service@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="claimed-schedule@test.com",
        status="in_progress",
        candidate_auth0_sub="candidate-claimed-schedule@test.com",
        candidate_email=None,
        claimed_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    await async_session.commit()

    principal = _principal(
        cs.invite_email,
        sub="candidate-claimed-schedule@test.com",
        email_verified=True,
    )
    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")
    sent_events: list[tuple[int, str | None]] = []

    async def _fake_send(*_args, candidate_session, correlation_id=None, **_kwargs):
        sent_events.append((candidate_session.id, correlation_id))
        return None, None

    monkeypatch.setattr(
        schedule_service.notification_service,
        "send_schedule_confirmation_emails",
        _fake_send,
    )

    now = datetime.now(UTC)
    start_at = now + timedelta(days=1)
    first = await schedule_service.schedule_candidate_session(
        async_session,
        token=cs.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
        correlation_id="req-1",
    )
    assert first.created is True
    assert first.candidate_session.schedule_locked_at is not None
    assert first.candidate_session.day_windows_json is not None
    for window in first.candidate_session.day_windows_json:
        assert isinstance(window["dayIndex"], int)
        assert isinstance(window["windowStartAt"], str)
        assert isinstance(window["windowEndAt"], str)
        assert (
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                window["windowStartAt"],
            )
            is not None
        )
        assert (
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                window["windowEndAt"],
            )
            is not None
        )
    assert sent_events == [(cs.id, "req-1")]

    # Idempotent retry: same schedule should not conflict and should not resend email.
    second = await schedule_service.schedule_candidate_session(
        async_session,
        token=cs.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
    )
    assert second.created is False
    assert len(sent_events) == 1

    with pytest.raises(ApiError) as excinfo:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=cs.token,
            principal=principal,
            scheduled_start_at=start_at + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=now,
        )
    assert excinfo.value.status_code == status.HTTP_409_CONFLICT
    assert excinfo.value.error_code == "SCHEDULE_ALREADY_SET"

    # Backfill path when lock exists but day_windows_json was empty.
    cs.day_windows_json = None
    await async_session.commit()
    refill = await schedule_service.schedule_candidate_session(
        async_session,
        token=cs.token,
        principal=principal,
        scheduled_start_at=start_at,
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=now,
    )
    assert refill.created is False
    assert refill.candidate_session.day_windows_json is not None


@pytest.mark.asyncio
async def test_schedule_candidate_session_validation_and_claim_errors(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="schedule-service-errors@test.com"
    )
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    claimed = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="claimed-errors@test.com",
        status="in_progress",
        candidate_auth0_sub="candidate-claimed-errors@test.com",
        claimed_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    unclaimed = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="unclaimed-errors@test.com",
    )
    await async_session.commit()

    email_service = EmailService(MemoryEmailProvider(), sender="noreply@test.com")
    claimed_principal = _principal(
        claimed.invite_email,
        sub="candidate-claimed-errors@test.com",
        email_verified=True,
    )

    with pytest.raises(ApiError) as past_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) - timedelta(minutes=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert past_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert past_exc.value.error_code == "SCHEDULE_START_IN_PAST"

    with pytest.raises(ApiError) as tz_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="Bad/Timezone",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert tz_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert tz_exc.value.error_code == "SCHEDULE_INVALID_TIMEZONE"

    # Bad simulation day-window config should map to schedule invalid window.
    simulation.day_window_start_local = time(hour=17, minute=0)
    simulation.day_window_end_local = time(hour=9, minute=0)
    await async_session.commit()
    with pytest.raises(ApiError) as window_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=claimed.token,
            principal=claimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=2),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert window_exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert window_exc.value.error_code == "SCHEDULE_INVALID_WINDOW"

    unclaimed_principal = _principal(unclaimed.invite_email)
    with pytest.raises(ApiError) as unclaimed_exc:
        await schedule_service.schedule_candidate_session(
            async_session,
            token=unclaimed.token,
            principal=unclaimed_principal,
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
            candidate_timezone="America/New_York",
            email_service=email_service,
            now=datetime.now(UTC),
        )
    assert unclaimed_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert unclaimed_exc.value.error_code == "SCHEDULE_NOT_CLAIMED"

    # Notification failures are swallowed after persistence.
    simulation.day_window_start_local = time(hour=9, minute=0)
    simulation.day_window_end_local = time(hour=17, minute=0)
    claimed.schedule_locked_at = None
    claimed.scheduled_start_at = None
    claimed.candidate_timezone = None
    claimed.day_windows_json = None
    await async_session.commit()

    async def _raise_send(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        schedule_service.notification_service,
        "send_schedule_confirmation_emails",
        _raise_send,
    )
    result = await schedule_service.schedule_candidate_session(
        async_session,
        token=claimed.token,
        principal=claimed_principal,
        scheduled_start_at=datetime.now(UTC) + timedelta(days=3),
        candidate_timezone="America/New_York",
        email_service=email_service,
        now=datetime.now(UTC),
    )
    assert result.created is True
    assert result.candidate_session.schedule_locked_at is not None


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


def test_schedule_service_internal_helpers_cover_edge_cases() -> None:
    principal = _principal("owner@test.com", sub="candidate-owner@test.com")
    cs = SimpleNamespace(
        invite_email="owner@test.com",
        candidate_auth0_sub="candidate-owner@test.com",
        claimed_at=datetime.now(UTC),
        candidate_auth0_email=None,
        candidate_email=None,
    )
    assert schedule_service._require_claimed_ownership(cs, principal) is True
    assert cs.candidate_auth0_email == "owner@test.com"
    assert cs.candidate_email == "owner@test.com"

    no_email_principal = _principal("", sub="candidate-", email_verified=True)
    with pytest.raises(ApiError) as no_email_exc:
        schedule_service._require_claimed_ownership(cs, no_email_principal)
    assert no_email_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert no_email_exc.value.error_code == "CANDIDATE_AUTH_EMAIL_MISSING"

    mismatch_principal = _principal("other@test.com", sub="candidate-other@test.com")
    with pytest.raises(ApiError) as mismatch_exc:
        schedule_service._require_claimed_ownership(cs, mismatch_principal)
    assert mismatch_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert mismatch_exc.value.error_code == "CANDIDATE_INVITE_EMAIL_MISMATCH"

    unclaimed = SimpleNamespace(
        invite_email="owner@test.com",
        candidate_auth0_sub=None,
        claimed_at=None,
        candidate_auth0_email=None,
        candidate_email=None,
    )
    with pytest.raises(ApiError) as unclaimed_exc:
        schedule_service._require_claimed_ownership(unclaimed, principal)
    assert unclaimed_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert unclaimed_exc.value.error_code == "SCHEDULE_NOT_CLAIMED"

    claimed_by_other = SimpleNamespace(
        invite_email="owner@test.com",
        candidate_auth0_sub="candidate-other@test.com",
        claimed_at=datetime.now(UTC),
        candidate_auth0_email=None,
        candidate_email=None,
    )
    with pytest.raises(ApiError) as sub_exc:
        schedule_service._require_claimed_ownership(claimed_by_other, principal)
    assert sub_exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert sub_exc.value.error_code == "CANDIDATE_SESSION_ALREADY_CLAIMED"

    assert schedule_service._schedule_matches(
        candidate_session=SimpleNamespace(
            scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_timezone="America/New_York",
        ),
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
    )
    assert not schedule_service._schedule_matches(
        candidate_session=SimpleNamespace(
            scheduled_start_at=None,
            candidate_timezone="America/New_York",
        ),
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
    )
    assert not schedule_service._schedule_matches(
        candidate_session=SimpleNamespace(
            scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_timezone="  ",
        ),
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
    )
    assert schedule_service._default_window_times(SimpleNamespace()) == (
        time(hour=9, minute=0),
        time(hour=17, minute=0),
    )
