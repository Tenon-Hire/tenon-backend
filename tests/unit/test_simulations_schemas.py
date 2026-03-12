import pytest
from pydantic import ValidationError

import app.schemas.simulations as simulation_schemas
from app.domains.simulations.ai_config import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
)
from app.domains.simulations.schemas import (
    SimulationDayWindowOverride,
    SimulationDetailTask,
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_eval_enabled_by_day,
    normalize_role_level,
    resolve_simulation_ai_fields,
)


def test_simulation_detail_task_serializes_optional_fields():
    task = SimulationDetailTask(
        dayIndex=1,
        title="Task",
        type="code",
        description=None,
        rubric=None,
        maxScore=10,
        preProvisioned=True,
        templateRepoFullName="org/repo",
    )

    serialized = task.model_dump()
    assert serialized["maxScore"] == 10
    assert serialized["preProvisioned"] is True
    assert serialized["templateRepoFullName"] == "org/repo"


def test_simulation_schema_helpers_cover_edge_cases():
    assert normalize_role_level(None) is None
    assert normalize_role_level("   ") is None
    assert normalize_role_level(" Mid ") == "mid"
    assert normalize_role_level("Wizard") is None

    with pytest.raises(ValueError):
        normalize_eval_enabled_by_day("not-a-map", strict=True)

    assert normalize_eval_enabled_by_day("not-a-map", strict=False) is None
    assert normalize_eval_enabled_by_day({"1": "yes", "9": True}, strict=False) == {}

    assert build_simulation_company_context({"unknown": "x"}) is None
    ai_config = build_simulation_ai_config(
        notice_version="",
        notice_text=None,
        eval_enabled_by_day={"1": True},
    )
    assert ai_config is not None
    assert ai_config.notice_version == "mvp1"
    assert ai_config.notice_text is not None
    assert ai_config.eval_enabled_by_day == {
        "1": True,
        "2": True,
        "3": True,
        "4": True,
        "5": True,
    }


def test_simulation_day_window_override_validation_and_serializer():
    with pytest.raises(ValidationError):
        SimulationDayWindowOverride.model_validate(
            {"startLocal": "10:00", "endLocal": "09:00"}
        )

    override = SimulationDayWindowOverride.model_validate(
        {"startLocal": "10:00", "endLocal": "18:00"}
    )
    assert override.model_dump() == {"startLocal": "10:00", "endLocal": "18:00"}


def test_resolve_simulation_ai_fields_ignores_overlong_notice_values():
    notice_version, notice_text, eval_enabled_by_day = resolve_simulation_ai_fields(
        notice_version="v" * (simulation_schemas.MAX_AI_NOTICE_VERSION_CHARS + 1),
        notice_text="n" * (simulation_schemas.MAX_AI_NOTICE_TEXT_CHARS + 1),
        eval_enabled_by_day=None,
    )

    assert notice_version == AI_NOTICE_DEFAULT_VERSION
    assert notice_text == AI_NOTICE_DEFAULT_TEXT
    assert eval_enabled_by_day == {
        "1": True,
        "2": True,
        "3": True,
        "4": True,
        "5": True,
    }


def test_build_simulation_ai_config_falls_back_on_validation_error(monkeypatch):
    def _broken_resolver(**_kwargs):
        return "mvp-custom", "notice", {"1": "not-a-bool"}

    monkeypatch.setattr(
        simulation_schemas, "resolve_simulation_ai_fields", _broken_resolver
    )

    ai_config = build_simulation_ai_config(
        notice_version="mvp-custom",
        notice_text="notice",
        eval_enabled_by_day={"1": False},
    )
    assert ai_config is not None
    assert ai_config.notice_version == AI_NOTICE_DEFAULT_VERSION
    assert ai_config.notice_text == AI_NOTICE_DEFAULT_TEXT
    assert ai_config.eval_enabled_by_day == {
        "1": True,
        "2": True,
        "3": True,
        "4": True,
        "5": True,
    }
