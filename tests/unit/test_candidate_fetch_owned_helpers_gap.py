"""
GAP-FILLING TESTS: app/services/candidate_sessions/fetch_owned_helpers.py

Gap identified:
- Missing fail-closed branch coverage when SQLAlchemy marks `simulation` as loaded
  but the value is `None` in `_loaded_simulation_status`.

These tests supplement:
- tests/unit/test_candidate_fetch_owned_helpers.py
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.domains import CandidateSession
from app.services.candidate_sessions.fetch_owned_helpers import ensure_can_access


def test_ensure_can_access_rejects_loaded_none_simulation_relationship():
    session = CandidateSession()
    session.simulation = None
    session.expires_at = None

    with pytest.raises(HTTPException) as excinfo:
        ensure_can_access(session, object(), now=datetime.now(UTC))

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Candidate session not found"
