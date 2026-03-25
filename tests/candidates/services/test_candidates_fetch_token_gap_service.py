"""
GAP-FILLING TESTS: app/candidates/candidate_sessions/services/*fetch_token*_service.py

Gap identified:
- Missing coverage for `_loaded_simulation_status` defensive branches:
  - SQLAlchemy inspection fallback path (`NoInspectionAvailable`).
  - Fail-closed behavior when `simulation` relationship is unloaded.
  - Fail-closed behavior when loaded `simulation` relationship is `None`.
- Missing coverage for `_ensure_simulation_not_terminated` rejection branch.

These tests supplement:
- tests/candidates/services/test_candidates_fetch_token_service.py
- tests/candidates/services/test_candidates_fetch_owned_helpers_service.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_token_service as fetch_token,
)
from app.shared.database.shared_database_models_model import CandidateSession
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)


def test_loaded_simulation_status_uses_fallback_for_non_mapped_objects():
    session = SimpleNamespace(simulation=SimpleNamespace(status="active_inviting"))
    assert fetch_token._loaded_simulation_status(session) == "active_inviting"


def test_loaded_simulation_status_rejects_unloaded_relationship():
    session = CandidateSession()

    with pytest.raises(HTTPException) as excinfo:
        fetch_token._loaded_simulation_status(session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"


def test_loaded_simulation_status_rejects_loaded_none_relationship():
    session = CandidateSession()
    session.simulation = None

    with pytest.raises(HTTPException) as excinfo:
        fetch_token._loaded_simulation_status(session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"


def test_ensure_simulation_not_terminated_rejects_token():
    session = SimpleNamespace(
        simulation=SimpleNamespace(status=SIMULATION_STATUS_TERMINATED)
    )

    with pytest.raises(HTTPException) as excinfo:
        fetch_token._ensure_simulation_not_terminated(session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invalid invite token"
