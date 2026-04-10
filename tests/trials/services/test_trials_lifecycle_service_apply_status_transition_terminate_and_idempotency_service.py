from __future__ import annotations

from tests.trials.services.trials_lifecycle_service_utils import *


def test_apply_status_transition_terminate_and_idempotency():
    now = datetime.now(UTC)
    sim = _trial(sim_service.TRIAL_STATUS_READY_FOR_REVIEW)
    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.TRIAL_STATUS_TERMINATED,
        changed_at=now,
    )
    assert changed is True
    assert sim.status == sim_service.TRIAL_STATUS_TERMINATED
    assert sim.terminated_at == now

    unchanged = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.TRIAL_STATUS_TERMINATED,
        changed_at=datetime.now(UTC),
    )
    assert unchanged is False
    assert sim.terminated_at == now
