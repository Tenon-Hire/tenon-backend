"""Application module for media routes media fake storage routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.integrations.storage_media import StorageMediaProvider
from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.integrations.storage_media.integrations_storage_media_storage_media_fake_provider_client import (
    FakeStorageMediaProvider,
)
from app.shared.http.dependencies.shared_http_dependencies_storage_media_utils import (
    get_media_storage_provider,
)

router = APIRouter(prefix="/storage/fake", tags=["recordings"])


def _require_fake_provider(
    storage_provider: StorageMediaProvider,
) -> FakeStorageMediaProvider:
    if not isinstance(storage_provider, FakeStorageMediaProvider):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fake media storage routes are unavailable",
        )
    return storage_provider


def _unprocessable(detail: str, exc: Exception | None = None) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
    ) from exc


@router.put(
    "/upload",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Object uploaded"},
        status.HTTP_403_FORBIDDEN: {"description": "Signed URL rejected"},
        status.HTTP_404_NOT_FOUND: {"description": "Fake storage disabled"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Upload rejected"},
    },
)
async def fake_storage_upload_route(
    request: Request,
    key: Annotated[str, Query(..., min_length=1)],
    contentType: Annotated[str, Query(..., min_length=1)],
    sizeBytes: Annotated[int, Query(..., gt=0)],
    expiresAt: Annotated[int, Query(..., gt=0)],
    sig: Annotated[str, Query(..., min_length=16)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
    durationSeconds: Annotated[int | None, Query(gt=0)] = None,
) -> Response:
    """Accept a signed fake-storage upload for local live validation."""
    provider = _require_fake_provider(storage_provider)
    try:
        safe_key = provider.validate_signed_upload_request(
            key=key,
            content_type=contentType,
            size_bytes=sizeBytes,
            expires_at=expiresAt,
            signature=sig,
            duration_seconds=durationSeconds,
        )
    except StorageMediaError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_403_FORBIDDEN
            if "signature" in detail.lower() or "expired" in detail.lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    body = await request.body()
    if len(body) != int(sizeBytes):
        _unprocessable("Uploaded object size does not match expected size")
    try:
        provider.write_object_bytes(
            safe_key,
            content_type=contentType,
            data=body,
            duration_seconds=durationSeconds,
        )
    except StorageMediaError as exc:
        _unprocessable(str(exc), exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/download",
    responses={
        status.HTTP_200_OK: {"description": "Object downloaded"},
        status.HTTP_403_FORBIDDEN: {"description": "Signed URL rejected"},
        status.HTTP_404_NOT_FOUND: {"description": "Object not found"},
    },
)
async def fake_storage_download_route(
    key: Annotated[str, Query(..., min_length=1)],
    expiresAt: Annotated[int, Query(..., gt=0)],
    sig: Annotated[str, Query(..., min_length=16)],
    storage_provider: Annotated[
        StorageMediaProvider, Depends(get_media_storage_provider)
    ],
):
    """Serve a signed fake-storage download for local browser and worker use."""
    provider = _require_fake_provider(storage_provider)
    try:
        safe_key = provider.validate_signed_download_request(
            key=key,
            expires_at=expiresAt,
            signature=sig,
        )
    except StorageMediaError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_403_FORBIDDEN
            if "signature" in detail.lower() or "expired" in detail.lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    metadata = provider.get_object_metadata(safe_key)
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded object not found",
        )
    try:
        object_path = provider.object_path(safe_key)
    except StorageMediaError as exc:
        _unprocessable(str(exc), exc)
    if not object_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded object not found",
        )
    filename = safe_key.rsplit("/", 1)[-1]
    return FileResponse(
        object_path,
        media_type=metadata.content_type,
        filename=filename,
    )


__all__ = [
    "fake_storage_download_route",
    "fake_storage_upload_route",
    "router",
]
