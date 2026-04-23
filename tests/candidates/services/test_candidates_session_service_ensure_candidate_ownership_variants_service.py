from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


def test_ensure_candidate_ownership_variants():
    principal = _principal("owner@example.com", email_verified=False)
    cs = type(
        "CS",
        (),
        {
            "invite_email": "owner@example.com",
            "candidate_auth0_sub": "auth0|owner@example.com",
            "candidate_email": None,
            "candidate_auth0_email": None,
            "status": "in_progress",
        },
    )()
    changed = cs_service._ensure_candidate_ownership(
        cs, principal, now=datetime.now(UTC)
    )
    assert changed is True
    assert cs.candidate_email == "owner@example.com"

    cs_different = type(
        "CS",
        (),
        {
            "invite_email": "owner@example.com",
            "candidate_auth0_sub": "other",
            "status": "in_progress",
        },
    )()
    with pytest.raises(HTTPException) as excinfo:
        cs_service._ensure_candidate_ownership(
            cs_different, principal, now=datetime.now(UTC)
        )
    assert (
        getattr(excinfo.value, "error_code", None)
        == "CANDIDATE_SESSION_ALREADY_CLAIMED"
    )


def test_ensure_candidate_ownership_allows_unverified_email_claims_in_local_env(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ENV", "local")
    principal = _principal("owner@example.com", email_verified=False)
    cs = type(
        "CS",
        (),
        {
            "invite_email": "owner@example.com",
            "candidate_auth0_sub": None,
            "candidate_email": None,
            "candidate_auth0_email": None,
            "status": "in_progress",
        },
    )()
    changed = cs_service._ensure_candidate_ownership(
        cs, principal, now=datetime.now(UTC)
    )
    assert changed is True
    assert cs.candidate_auth0_sub == principal.sub
    assert cs.candidate_auth0_email == "owner@example.com"
    assert cs.candidate_email == "owner@example.com"
