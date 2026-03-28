"""Application module for recruiters routes admin routes recruiters admin routes demo ops routes workflows."""

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
    summary="Reset Candidate Session",
    description=(
        "Reset a candidate session state during demo-mode operations for controlled QA"
        " or replay flows."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid reset request payload."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Demo mode disabled or target session not found."
        },
    },
)
async def reset_candidate_session(
    candidate_session_id: Annotated[int, Path(..., gt=0)],
    payload: CandidateSessionResetRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> CandidateSessionResetResponse:
    """Reset candidate session."""
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
    summary="Requeue Job",
    description=(
        "Force a durable background job back to queued state for demo-mode"
        " recovery/testing."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Job cannot be requeued."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Demo mode disabled or target job not found."
        },
    },
)
async def requeue_job(
    job_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    payload: JobRequeueRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> JobRequeueResponse:
    """Requeue job."""
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
    summary="Use Simulation Fallback",
    description=(
        "Apply a fallback scenario version to a simulation when generated content"
        " must be overridden in demo mode."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Fallback request is invalid."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Demo mode disabled or simulation not found."
        },
    },
)
async def use_simulation_fallback(
    simulation_id: Annotated[int, Path(..., gt=0)],
    payload: SimulationFallbackRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
) -> SimulationFallbackResponse:
    """Use simulation fallback."""
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
    summary="Purge Media Retention",
    description=(
        "Run retention cleanup for recording assets and mark expired media as"
        " purged in demo environments."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Retention inputs are invalid."},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Demo mode disabled."},
    },
)
async def purge_media_retention(
    payload: MediaRetentionPurgeRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actor: Annotated[DemoAdminActor, Depends(require_demo_mode_admin)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
) -> MediaRetentionPurgeResponse:
    """Purge media retention."""
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
