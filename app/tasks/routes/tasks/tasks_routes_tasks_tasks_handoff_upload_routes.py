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
