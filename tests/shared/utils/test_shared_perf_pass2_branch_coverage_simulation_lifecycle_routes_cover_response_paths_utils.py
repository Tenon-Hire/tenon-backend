from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_simulation_lifecycle_routes_cover_response_paths(monkeypatch):
    activated_at = datetime.now(UTC)
    terminated_at = datetime.now(UTC)
    simulation = SimpleNamespace(
        id=44,
        status="active",
        activated_at=activated_at,
        terminated_at=terminated_at,
    )
    terminated = SimpleNamespace(simulation=simulation, cleanup_job_ids=["job-1"])

    monkeypatch.setattr(
        lifecycle_route, "ensure_recruiter_or_none", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        lifecycle_route.sim_service,
        "activate_simulation",
        _async_return(simulation),
    )
    monkeypatch.setattr(
        lifecycle_route.sim_service,
        "terminate_simulation_with_cleanup",
        _async_return(terminated),
    )
    monkeypatch.setattr(
        lifecycle_route.sim_service,
        "normalize_simulation_status_or_raise",
        lambda _status: "active_inviting",
    )

    payload = SimpleNamespace(confirm=True, reason="cleanup")
    user = SimpleNamespace(id=7)
    activated = await lifecycle_route.activate_simulation(44, payload, object(), user)
    terminated_response = await lifecycle_route.terminate_simulation(
        44, payload, object(), user
    )
    assert activated.status == "active_inviting"
    assert activated.activatedAt == activated_at
    assert terminated_response.status == "active_inviting"
    assert terminated_response.terminatedAt == terminated_at
    assert terminated_response.cleanupJobIds == ["job-1"]
