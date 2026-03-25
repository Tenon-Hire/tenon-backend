"""
GAP-FILLING TESTS: app/candidates/candidate_sessions/services/*fetch_owned_helpers*_service.py

Gap identified:
- Missing fail-closed branch coverage when SQLAlchemy marks `simulation` as loaded
  but the value is `None` in `_loaded_simulation_status`.

These tests supplement:
- tests/candidates/services/test_candidates_fetch_owned_helpers_service.py
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_owned_helpers_service import (
    ensure_can_access,
)
from app.shared.database.shared_database_models_model import CandidateSession


def test_ensure_can_access_rejects_loaded_none_simulation_relationship():
    session = CandidateSession()
    session.simulation = None
    session.expires_at = None

    with pytest.raises(HTTPException) as excinfo:
        ensure_can_access(session, object(), now=datetime.now(UTC))

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Candidate session not found"
