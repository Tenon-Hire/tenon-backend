from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.simulations import SimulationCreate


def _base_payload() -> dict:
    return {
        "title": "Backend Node Simulation",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "mid",
        "focus": "Emphasize code quality and test discipline.",
    }


def test_simulation_create_rejects_invalid_seniority() -> None:
    payload = _base_payload()
    payload["seniority"] = "manager"
    with pytest.raises(ValidationError):
        SimulationCreate.model_validate(payload)


def test_simulation_create_rejects_oversized_focus() -> None:
    payload = _base_payload()
    payload["focus"] = "x" * 1001
    with pytest.raises(ValidationError):
        SimulationCreate.model_validate(payload)


def test_simulation_create_rejects_extra_company_context_keys() -> None:
    payload = _base_payload()
    payload["companyContext"] = {"domain": "social", "unknown": "value"}
    with pytest.raises(ValidationError):
        SimulationCreate.model_validate(payload)


def test_simulation_create_rejects_ai_invalid_day_key() -> None:
    payload = _base_payload()
    payload["ai"] = {"evalEnabledByDay": {"6": True}}
    with pytest.raises(ValidationError):
        SimulationCreate.model_validate(payload)


def test_simulation_create_rejects_ai_non_bool_value() -> None:
    payload = _base_payload()
    payload["ai"] = {"evalEnabledByDay": {"1": "true"}}
    with pytest.raises(ValidationError):
        SimulationCreate.model_validate(payload)


def test_simulation_create_normalizes_aliases_and_day_keys() -> None:
    payload = _base_payload()
    payload.pop("seniority")
    payload.pop("focus")
    payload["roleLevel"] = "Mid"
    payload["focusNotes"] = "Focus notes"
    payload["companyContext"] = {"productArea": "creator tools"}
    payload["ai"] = {"evalEnabledByDay": {1: True, "2": False}}

    parsed = SimulationCreate.model_validate(payload)

    assert parsed.seniority == "mid"
    assert parsed.focus == "Focus notes"
    assert parsed.company_context is not None
    assert parsed.company_context.product_area == "creator tools"
    assert parsed.ai is not None
    assert parsed.ai.eval_enabled_by_day == {"1": True, "2": False}
