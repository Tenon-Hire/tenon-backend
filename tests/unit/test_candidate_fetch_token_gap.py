"""
GAP-FILLING TESTS: app/services/candidate_sessions/fetch_token.py

Gap identified:
- Missing coverage for `_loaded_simulation_status` defensive branches:
  - SQLAlchemy inspection fallback path (`NoInspectionAvailable`).
  - Fail-closed behavior when `simulation` relationship is unloaded.
  - Fail-closed behavior when loaded `simulation` relationship is `None`.
- Missing coverage for `_ensure_simulation_not_terminated` rejection branch.

These tests supplement:
- tests/unit/test_candidate_session_service.py
- tests/unit/test_candidate_fetch_owned_helpers.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains import CandidateSession
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED
from app.services.candidate_sessions import fetch_token


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
