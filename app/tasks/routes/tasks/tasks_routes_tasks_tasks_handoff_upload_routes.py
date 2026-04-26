"""Application module for tasks routes tasks handoff upload routes workflows."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.storage_media import StorageMediaProvider, resolve_signed_url_ttl
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_SUPPLEMENTAL,
)
from app.media.services.media_services_media_handoff_upload_service import (
    complete_handoff_upload,
    get_handoff_status,
    init_handoff_upload,
)
from app.media.services.media_services_media_keys_service import recording_public_id
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.dependencies.shared_http_dependencies_storage_media_utils import (
    get_media_storage_provider,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    HandoffStatusResponse,
    HandoffUploadCompleteRequest,
    HandoffUploadCompleteResponse,
    HandoffUploadInitRequest,
    HandoffUploadInitResponse,
)

from .tasks_routes_tasks_tasks_handoff_upload_complete_handler import (
    complete_handoff_upload_route_impl,
)
from .tasks_routes_tasks_tasks_handoff_upload_init_handler import (
    init_handoff_upload_route_impl,
)
from .tasks_routes_tasks_tasks_handoff_upload_status_handler import (
    handoff_status_route_impl,
)
from .tasks_routes_tasks_tasks_handoff_upload_utils import (
    build_recording_status_payload,
    build_supplemental_status_payloads,
    build_transcript_status_payload,
    normalize_handoff_status_result,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{task_id}/handoff/upload/init",
    response_model=HandoffUploadInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Init Handoff Upload Route",
    description=(
        "Initialize candidate handoff recording upload and return signed upload"
        " instructions."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Candidate session access denied."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Task or candidate session not found."
        },
    },
)
async def init_handoff_upload_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: HandoffUploadInitRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
) -> HandoffUploadInitResponse:
    """Handle the init handoff upload API route."""
    return await init_handoff_upload_route_impl(
        task_id=task_id,
        payload=payload,
        candidate_session=candidate_session,
        db=db,
        storage_provider=storage_provider,
        init_handoff_upload_fn=init_handoff_upload,
        recording_public_id_fn=recording_public_id,
    )


@router.post(
    "/{task_id}/handoff/upload/complete",
    response_model=HandoffUploadCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Handoff Upload Route",
    description=(
        "Finalize a previously initialized handoff upload and bind recording"
        " metadata to the submission."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Candidate session access denied."},
        status.HTTP_404_NOT_FOUND: {"description": "Task or upload record not found."},
    },
)
async def complete_handoff_upload_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: HandoffUploadCompleteRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
) -> HandoffUploadCompleteResponse:
    """Handle the complete handoff upload API route."""
    return await complete_handoff_upload_route_impl(
        task_id=task_id,
        payload=payload,
        candidate_session=candidate_session,
        db=db,
        storage_provider=storage_provider,
        complete_handoff_upload_fn=complete_handoff_upload,
        recording_public_id_fn=recording_public_id,
    )


@router.get(
    "/{task_id}/handoff/status",
    response_model=HandoffStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Handoff Status Route",
    description=(
        "Return the current recording/transcript status for handoff tasks in"
        " the candidate session."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Candidate session access denied."},
        status.HTTP_404_NOT_FOUND: {
            "description": "Task or handoff recording not found."
        },
    },
)
async def handoff_status_route(
    task_id: Annotated[int, Path(..., ge=1)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
) -> HandoffStatusResponse:
    """Handle the handoff status API route."""
    recording, transcript, transcript_job = normalize_handoff_status_result(
        await get_handoff_status(
            db,
            candidate_session=candidate_session,
            task_id=task_id,
        )
    )
    supplemental_materials = []
    if db is not None:
        supplemental_materials = [
            asset
            for asset in await recordings_repo.list_for_task_session(
                db,
                candidate_session_id=candidate_session.id,
                task_id=task_id,
                asset_kind=RECORDING_ASSET_KIND_SUPPLEMENTAL,
            )
            if not recordings_repo.is_deleted_or_purged(asset)
        ]
    return await handoff_status_route_impl(
        task_id=task_id,
        candidate_session=candidate_session,
        db=db,
        storage_provider=storage_provider,
        recording=recording,
        transcript=transcript,
        transcript_job=transcript_job,
        supplemental_materials=supplemental_materials,
        is_downloadable_fn=recordings_repo.is_downloadable,
        resolve_signed_url_ttl_fn=resolve_signed_url_ttl,
        build_transcript_status_payload_fn=build_transcript_status_payload,
        build_recording_status_payload_fn=build_recording_status_payload,
        build_supplemental_status_payloads_fn=build_supplemental_status_payloads,
        logger=logger,
    )


__all__ = [
    "complete_handoff_upload_route",
    "handoff_status_route",
    "init_handoff_upload_route",
    "router",
]
