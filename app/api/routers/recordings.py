from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.candidate_access import require_candidate_principal
from app.core.auth.principal import Principal
from app.core.db import get_session
from app.domains.candidate_sessions import service as cs_service
from app.domains.recordings.schemas import RecordingDeleteResponse
from app.repositories.recordings import repository as recordings_repo
from app.services.media.keys import parse_recording_public_id
from app.services.media.privacy import delete_recording_asset

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post(
    "/{recording_id}/delete",
    response_model=RecordingDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_recording_route(
    recording_id: Annotated[str, Path(..., min_length=1, max_length=64)],
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> RecordingDeleteResponse:
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
