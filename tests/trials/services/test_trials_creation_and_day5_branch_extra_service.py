from __future__ import annotations

from types import SimpleNamespace

from app.trials.services import (
    trials_services_trials_creation_builder_service as creation_builder,
)
from app.trials.services import (
    trials_services_trials_day_five_contract_service as day5_contract,
)


def test_creation_builder_preferred_language_helper_ignores_blank_values():
    payload = SimpleNamespace(
        preferredLanguageFramework=" ", preferred_language_framework=""
    )

    assert creation_builder._resolve_preferred_language_framework(payload) is None
    assert creation_builder._resolve_tech_stack(payload, "Python") == ""


def test_day_five_contract_noops_when_tasks_omitted():
    trial = SimpleNamespace(
        day_window_overrides_enabled=False, day_window_overrides_json=None
    )

    day5_contract.enforce_day_five_trial_contract(trial, tasks=None)

    assert trial.day_window_overrides_enabled is True
    assert (
        trial.day_window_overrides_json
        == day5_contract.canonical_day_five_window_override()
    )
