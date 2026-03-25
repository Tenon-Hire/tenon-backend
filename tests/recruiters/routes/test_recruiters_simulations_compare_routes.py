from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.simulations.routes.simulations_routes import (
    simulations_routes_simulations_routes_simulations_routes_candidates_compare_routes as compare_router,
)


@pytest.mark.asyncio
async def test_list_simulation_candidates_compare_logs_and_returns_payload(monkeypatch):
    user = SimpleNamespace(id=77)
    summary = {
        "simulationId": 9,
        "candidates": [
            {
                "candidateSessionId": 11,
                "candidateName": "Candidate A",
                "candidateDisplayName": "Candidate A",
                "status": "scheduled",
                "fitProfileStatus": "none",
                "overallFitScore": None,
                "recommendation": None,
                "dayCompletion": {
                    "1": False,
                    "2": False,
                    "3": False,
                    "4": False,
                    "5": False,
                },
                "updatedAt": datetime.now(UTC),
            }
        ],
    }

    async def _list_compare(*_args, **_kwargs):
        return summary

    log_events: list[str] = []
    monkeypatch.setattr(compare_router, "ensure_recruiter", lambda _u: None)
    monkeypatch.setattr(
        compare_router.sim_service, "list_candidates_compare_summary", _list_compare
    )
    monkeypatch.setattr(
        compare_router.logger,
        "info",
        lambda message, *_args: log_events.append(str(message)),
    )
    response = await compare_router.list_simulation_candidates_compare(
        simulation_id=9,
        db=SimpleNamespace(),
        user=user,
    )
    assert response.simulationId == 9
    assert response.candidates[0].candidateSessionId == 11
    assert any("Simulation candidates compare fetched" in line for line in log_events)
