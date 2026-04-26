from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import settings
from app.trials.schemas.trials_schemas_trials_core_schema import (
    TrialCreate,
)


def _base_payload() -> dict:
    return {
        "title": "Backend Node Trial",
        "role": "Backend Engineer",
        "seniority": "mid",
    }


def test_trial_create_rejects_invalid_seniority() -> None:
    payload = _base_payload()
    payload["seniority"] = "manager"
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_rejects_oversized_focus() -> None:
    payload = _base_payload()
    payload["focus"] = "x" * 1001
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_rejects_extra_company_context_keys() -> None:
    payload = _base_payload()
    payload["companyContext"] = {"domain": "social", "unknown": "value"}
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_rejects_ai_invalid_day_key() -> None:
    payload = _base_payload()
    payload["ai"] = {"evalEnabledByDay": {"6": True}}
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_rejects_ai_non_bool_value() -> None:
    payload = _base_payload()
    payload["ai"] = {"evalEnabledByDay": {"1": "true"}}
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_normalizes_aliases_and_day_keys() -> None:
    payload = _base_payload()
    payload.pop("seniority")
    payload["focusNotes"] = "Focus notes"
    payload["roleLevel"] = "Mid"
    payload["companyContext"] = {"productArea": "creator tools"}
    payload["ai"] = {"evalEnabledByDay": {1: True, "2": False}}

    parsed = TrialCreate.model_validate(payload)

    assert parsed.seniority == "mid"
    assert parsed.focus == "Focus notes"
    assert parsed.company_context is not None
    assert parsed.company_context.product_area == "creator tools"
    assert parsed.ai is not None
    assert parsed.ai.eval_enabled_by_day == {"1": True, "2": False}


def test_trial_create_allows_pivoted_payload_without_legacy_fields() -> None:
    payload = _base_payload()
    payload["preferredLanguageFramework"] = "TypeScript/Node"

    parsed = TrialCreate.model_validate(payload)

    assert parsed.focus is None
    assert parsed.preferred_language_framework == "TypeScript/Node"


def test_trial_create_accepts_snake_case_preferred_language_framework() -> None:
    payload = _base_payload()
    payload["preferred_language_framework"] = "Python/FastAPI"

    parsed = TrialCreate.model_validate(payload)

    assert parsed.preferred_language_framework == "Python/FastAPI"


def test_trial_create_rejects_retired_template_inputs() -> None:
    for field_name in ("techStack", "tech_stack", "templateKey", "template_repository"):
        payload = _base_payload()
        payload[field_name] = "retired"
        with pytest.raises(ValidationError):
            TrialCreate.model_validate(payload)


def test_trial_create_rejects_invalid_day_window_bounds() -> None:
    payload = _base_payload()
    payload["dayWindowStartLocal"] = "17:00"
    payload["dayWindowEndLocal"] = "09:00"
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)


def test_trial_create_day_window_overrides_feature_flag(monkeypatch) -> None:
    payload = _base_payload()
    payload["dayWindowOverridesEnabled"] = True
    payload["dayWindowOverrides"] = {"9": {"startLocal": "10:00", "endLocal": "18:00"}}

    monkeypatch.setattr(settings, "SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED", False)
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(payload)

    monkeypatch.setattr(settings, "SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED", True)
    parsed = TrialCreate.model_validate(payload)
    assert parsed.dayWindowOverrides is not None
    assert parsed.dayWindowOverrides["9"].start_local.hour == 10
    assert parsed.dayWindowOverrides["9"].end_local.hour == 18


def test_trial_create_day_window_overrides_validation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED", True)

    bad_key = _base_payload()
    bad_key["dayWindowOverridesEnabled"] = True
    bad_key["dayWindowOverrides"] = {"8": {"startLocal": "10:00", "endLocal": "18:00"}}
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(bad_key)

    bad_shape = _base_payload()
    bad_shape["dayWindowOverridesEnabled"] = True
    bad_shape["dayWindowOverrides"] = "not-an-object"
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(bad_shape)

    missing_enabled = _base_payload()
    missing_enabled["dayWindowOverrides"] = {
        "9": {"startLocal": "10:00", "endLocal": "18:00"}
    }
    with pytest.raises(ValidationError):
        TrialCreate.model_validate(missing_enabled)


def test_trial_create_allows_explicit_null_day_window_overrides() -> None:
    payload = _base_payload()
    payload["dayWindowOverrides"] = None
    parsed = TrialCreate.model_validate(payload)
    assert parsed.dayWindowOverrides is None
