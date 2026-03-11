from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.candidate_sessions import candidate_session_from_headers
from app.api.dependencies.storage_media import get_media_storage_provider
from app.core.db import get_session
from app.domains import CandidateSession
from app.domains.submissions.schemas import (
    HandoffUploadCompleteRequest,
    HandoffUploadCompleteResponse,
    HandoffUploadInitRequest,
    HandoffUploadInitResponse,
)
from app.integrations.storage_media import StorageMediaProvider
from app.services.media.handoff_upload import (
    complete_handoff_upload,
    init_handoff_upload,
)
from app.services.media.keys import recording_public_id

router = APIRouter()


@router.post(
    "/{task_id}/handoff/upload/init",
    response_model=HandoffUploadInitResponse,
    status_code=status.HTTP_200_OK,
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
    """Create recording metadata and return signed upload URL."""
    recording, upload_url, expires_seconds = await init_handoff_upload(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
        content_type=payload.contentType,
        size_bytes=payload.sizeBytes,
        filename=payload.filename,
        storage_provider=storage_provider,
    )
    return HandoffUploadInitResponse(
        recordingId=recording_public_id(recording.id),
        uploadUrl=upload_url,
        expiresInSeconds=expires_seconds,
    )


@router.post(
    "/{task_id}/handoff/upload/complete",
    response_model=HandoffUploadCompleteResponse,
    status_code=status.HTTP_200_OK,
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
    """Mark recording upload as complete and ensure transcript placeholder exists."""
    recording = await complete_handoff_upload(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
        recording_id_value=payload.recordingId,
        storage_provider=storage_provider,
    )
    return HandoffUploadCompleteResponse(
        recordingId=recording_public_id(recording.id),
        status=recording.status,
    )


__all__ = ["complete_handoff_upload_route", "init_handoff_upload_route", "router"]
