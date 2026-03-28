"""Application module for tasks routes tasks handoff upload routes workflows."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.storage_media import StorageMediaProvider, resolve_signed_url_ttl
from app.media.repositories.recordings import repository as recordings_repo
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
    build_transcript_status_payload,
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
    return await handoff_status_route_impl(
        task_id=task_id,
        candidate_session=candidate_session,
        db=db,
        storage_provider=storage_provider,
        get_handoff_status_fn=get_handoff_status,
        is_downloadable_fn=recordings_repo.is_downloadable,
        resolve_signed_url_ttl_fn=resolve_signed_url_ttl,
        recording_public_id_fn=recording_public_id,
        build_transcript_status_payload_fn=build_transcript_status_payload,
        logger=logger,
    )


__all__ = [
    "complete_handoff_upload_route",
    "handoff_status_route",
    "init_handoff_upload_route",
    "router",
]
