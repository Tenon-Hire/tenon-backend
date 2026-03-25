from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.storage_media import StorageMediaProvider
from app.media.services.media_services_media_privacy_service import (
    purge_expired_media_assets,
)
from app.recruiters.routes.admin_routes.recruiters_routes_admin_routes_recruiters_admin_routes_demo_ops_responses_routes import (
    build_fallback_response,
    build_media_purge_response,
    build_requeue_response,
    build_reset_response,
)
from app.recruiters.schemas.recruiters_schemas_recruiters_admin_ops_schema import (
    CandidateSessionResetRequest,
    CandidateSessionResetResponse,
    JobRequeueRequest,
    JobRequeueResponse,
    MediaRetentionPurgeRequest,
    MediaRetentionPurgeResponse,
    SimulationFallbackRequest,
    SimulationFallbackResponse,
)
from app.recruiters.services import (
    recruiters_services_recruiters_admin_ops_service as admin_ops_service,
)
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils import (
    DemoAdminActor,
    require_demo_mode_admin,
)
from app.shared.http.dependencies.shared_http_dependencies_storage_media_utils import (
    get_media_storage_provider,
)

router = APIRouter()


@router.post(
    "/candidate_sessions/{candidate_session_id}/reset",
    response_model=CandidateSessionResetResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_candidate_session(
    candidate_session_id: Annotated[int, Path(..., gt=0)],
    payload: CandidateSessionResetRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> CandidateSessionResetResponse:
    result = await admin_ops_service.reset_candidate_session(
        db,
        actor=actor,
        candidate_session_id=candidate_session_id,
        target_state=payload.targetState,
        reason=payload.reason,
        override_if_evaluated=payload.overrideIfEvaluated,
        dry_run=payload.dryRun,
    )
    return build_reset_response(result)


@router.post(
    "/jobs/{job_id}/requeue",
    response_model=JobRequeueResponse,
    status_code=status.HTTP_200_OK,
)
async def requeue_job(
    job_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    payload: JobRequeueRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> JobRequeueResponse:
    result = await admin_ops_service.requeue_job(
        db,
        actor=actor,
        job_id=job_id,
        reason=payload.reason,
        force=payload.force,
    )
    return build_requeue_response(result)


@router.post(
    "/simulations/{simulation_id}/scenario/use_fallback",
    response_model=SimulationFallbackResponse,
    status_code=status.HTTP_200_OK,
)
async def use_simulation_fallback(
    simulation_id: Annotated[int, Path(..., gt=0)],
    payload: SimulationFallbackRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> SimulationFallbackResponse:
    result = await admin_ops_service.use_simulation_fallback_scenario(
        db,
        actor=actor,
        simulation_id=simulation_id,
        scenario_version_id=payload.scenarioVersionId,
        apply_to=payload.applyTo,
        reason=payload.reason,
        dry_run=payload.dryRun,
    )
    return build_fallback_response(result)


@router.post(
    "/media/purge",
    response_model=MediaRetentionPurgeResponse,
    status_code=status.HTTP_200_OK,
)
async def purge_media_retention(
    payload: MediaRetentionPurgeRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
) -> MediaRetentionPurgeResponse:
    del actor
    result = await purge_expired_media_assets(
        db,
        storage_provider=storage_provider,
        retention_days=payload.retentionDays,
        batch_limit=payload.batchLimit,
    )
    return build_media_purge_response(result)


__all__ = [
    "purge_media_retention",
    "requeue_job",
    "reset_candidate_session",
    "router",
    "use_simulation_fallback",
]
