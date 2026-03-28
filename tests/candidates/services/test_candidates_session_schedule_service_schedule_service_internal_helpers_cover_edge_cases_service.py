from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_schedule_service_utils import *


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
