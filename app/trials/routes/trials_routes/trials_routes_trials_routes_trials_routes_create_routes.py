"""Application module for trials routes trials routes trials routes create routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.shared.database import get_session
from app.trials import services as sim_service
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioVersionSummary,
    TaskOut,
    TrialCreate,
    TrialCreateResponse,
    build_trial_ai_config,
    build_trial_company_context,
    normalize_role_level,
)

router = APIRouter(prefix="/trials")


@router.post(
    "", response_model=TrialCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_trial(
    payload: TrialCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Create a trial and seed default tasks."""
    ensure_talent_partner_or_none(user)
    sim, created_tasks, scenario_job = await sim_service.create_trial_with_tasks(
        db, payload, user
    )
    raw_status = getattr(sim, "status", None)
    return TrialCreateResponse(
        id=sim.id,
        title=sim.title,
        role=sim.role,
        techStack=sim.tech_stack,
        seniority=normalize_role_level(sim.seniority) or sim.seniority,
        focus=sim.focus,
        companyContext=build_trial_company_context(
            getattr(sim, "company_context", None)
        ),
        ai=build_trial_ai_config(
            notice_version=getattr(sim, "ai_notice_version", None),
            notice_text=getattr(sim, "ai_notice_text", None),
            eval_enabled_by_day=getattr(sim, "ai_eval_enabled_by_day", None),
            prompt_overrides_json=getattr(sim, "ai_prompt_overrides_json", None),
        ),
        templateKey=sim.template_key,
        status=sim_service.normalize_trial_status_or_raise(raw_status),
        generatingAt=getattr(sim, "generating_at", None),
        readyForReviewAt=getattr(sim, "ready_for_review_at", None),
        activatedAt=getattr(sim, "activated_at", None),
        terminatedAt=getattr(sim, "terminated_at", None),
        scenarioVersionSummary=ScenarioVersionSummary(
            templateKey=getattr(sim, "template_key", None),
            scenarioTemplate=getattr(sim, "scenario_template", None),
        ),
        scenarioGenerationJobId=str(scenario_job.id),
        tasks=[
            TaskOut(id=t.id, day_index=t.day_index, type=t.type, title=t.title)
            for t in created_tasks
        ],
    )
