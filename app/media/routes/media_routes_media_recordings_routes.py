"""Application module for media routes media recordings routes workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.media.repositories.recordings import repository as recordings_repo
from app.media.schemas.media_schemas_media_recordings_schema import (
    RecordingDeleteResponse,
)
from app.media.services.media_services_media_keys_service import (
    parse_recording_public_id,
)
from app.media.services.media_services_media_privacy_service import (
    delete_recording_asset,
)
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post(
    "/{recording_id}/delete",
    response_model=RecordingDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Recording Route",
    description=(
        "Soft-delete a recording asset owned by the authenticated candidate"
        " session and revoke access links."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Candidate authentication required."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Candidate does not own session."},
        status.HTTP_404_NOT_FOUND: {"description": "Recording asset not found."},
    },
)
async def delete_recording_route(
    recording_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> RecordingDeleteResponse:
    """Handle the delete recording API route."""
    try:
        recording_id_value = parse_recording_public_id(recording_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    recording = await recordings_repo.get_by_id(db, recording_id_value)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording asset not found",
        )
    candidate_session = await cs_service.fetch_owned_session(
        db,
        recording.candidate_session_id,
        principal,
        now=datetime.now(UTC),
    )
    await delete_recording_asset(
        db,
        recording_id=recording_id_value,
        candidate_session=candidate_session,
    )
    return RecordingDeleteResponse(status="deleted")


__all__ = ["delete_recording_route", "router"]
