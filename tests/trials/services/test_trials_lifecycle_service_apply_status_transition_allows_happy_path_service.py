from __future__ import annotations

from tests.trials.services.trials_lifecycle_service_utils import *


def test_apply_status_transition_allows_happy_path():
    sim = _trial(sim_service.TRIAL_STATUS_DRAFT)
    at = datetime.now(UTC)

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.TRIAL_STATUS_GENERATING,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.TRIAL_STATUS_GENERATING
    assert sim.generating_at == at

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.TRIAL_STATUS_READY_FOR_REVIEW,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    assert sim.ready_for_review_at == at

    changed = sim_service.apply_status_transition(
        sim,
        target_status=sim_service.TRIAL_STATUS_ACTIVE_INVITING,
        changed_at=at,
    )
    assert changed is True
    assert sim.status == sim_service.TRIAL_STATUS_ACTIVE_INVITING
    assert sim.activated_at == at
