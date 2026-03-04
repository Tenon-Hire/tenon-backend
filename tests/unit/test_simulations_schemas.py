import pytest

from app.domains.simulations.schemas import (
    SimulationDetailTask,
    build_simulation_ai_config,
    build_simulation_company_context,
    normalize_eval_enabled_by_day,
    normalize_role_level,
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
    assert (
        build_simulation_ai_config(
            notice_version="",
            notice_text=None,
            eval_enabled_by_day={"1": True},
        )
        is None
    )
