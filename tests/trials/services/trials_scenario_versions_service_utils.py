from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioEditAudit,
    ScenarioVersion,
    Task,
    Trial,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.schemas.trials_schemas_trials_core_schema import (
    MAX_SCENARIO_NOTES_CHARS,
    MAX_SCENARIO_RUBRIC_BYTES,
    MAX_SCENARIO_STORYLINE_CHARS,
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
)
from app.trials.services import scenario_versions as scenario_service
from tests.shared.factories import create_talent_partner, create_trial


async def _create_bare_trial(async_session, talent_partner):
    sim = Trial(
        company_id=talent_partner.company_id,
        title="Scenario Service Sim",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="mid",
        focus="Scenario focus",
        scenario_template="default-5day-node-postgres",
        created_by=talent_partner.id,
        template_key="python-fastapi",
        status="generating",
        generating_at=datetime.now(UTC),
    )
    async_session.add(sim)
    await async_session.flush()

    day2 = Task(
        trial_id=sim.id,
        day_index=2,
        type="code",
        title="Day 2",
        description="Code prompt",
    )
    day1 = Task(
        trial_id=sim.id,
        day_index=1,
        type="design",
        title="Day 1",
        description="Design prompt",
    )
    async_session.add_all([day2, day1])
    await async_session.flush()
    return sim, [day2, day1]


def _assert_patch_invalid(merged_state: dict, detail_fragment: str) -> None:
    with pytest.raises(ApiError) as excinfo:
        scenario_service._validate_and_normalize_merged_scenario_state(merged_state)
    assert excinfo.value.error_code == "SCENARIO_PATCH_INVALID"
    assert detail_fragment in str(excinfo.value.detail)


__all__ = [name for name in globals() if not name.startswith("__")]
