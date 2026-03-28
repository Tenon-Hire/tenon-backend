from __future__ import annotations

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


def test_ensure_candidate_ownership_does_not_overwrite_claimed_at_when_present():
    now = datetime.now(UTC)
    claimed_at = datetime(2025, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        invite_email="candidate@example.com",
        candidate_auth0_sub=None,
        candidate_auth0_email="candidate@example.com",
        candidate_email="candidate@example.com",
        claimed_at=claimed_at,
    )
    principal = SimpleNamespace(
        email="candidate@example.com",
        sub="auth0|candidate",
        claims={"email_verified": True},
    )

    changed = ownership_service.ensure_candidate_ownership(
        candidate_session,
        principal,
        now=now,
    )

    assert changed is True
    assert candidate_session.candidate_auth0_sub == "auth0|candidate"
    assert candidate_session.claimed_at == claimed_at
