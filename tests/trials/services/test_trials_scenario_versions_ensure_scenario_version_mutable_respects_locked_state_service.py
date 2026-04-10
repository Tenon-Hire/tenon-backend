from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


def test_ensure_scenario_version_mutable_respects_locked_state():
    unlocked = ScenarioVersion(
        trial_id=1,
        version_index=1,
        status="ready",
        storyline_md="x",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="",
        template_key="python-fastapi",
        tech_stack="Python",
        seniority="mid",
    )
    scenario_service.ensure_scenario_version_mutable(unlocked)

    locked = ScenarioVersion(
        trial_id=1,
        version_index=1,
        status="locked",
        storyline_md="x",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="",
        template_key="python-fastapi",
        tech_stack="Python",
        seniority="mid",
    )
    with pytest.raises(ApiError) as excinfo:
        scenario_service.ensure_scenario_version_mutable(locked)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_LOCKED"
