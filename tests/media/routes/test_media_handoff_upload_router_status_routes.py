from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_handoff_upload_routes as handoff_upload_router,
)


@pytest.mark.asyncio
async def test_handoff_status_route_shapes_response(monkeypatch):
    async def _stub_status(db, *, candidate_session, task_id: int):
        del db, candidate_session, task_id
        return (
            SimpleNamespace(
                id=44, status="processing", storage_key="recordings/44.mp4"
            ),
            SimpleNamespace(status="processing"),
        )

    monkeypatch.setattr(handoff_upload_router, "get_handoff_status", _stub_status)
    result = await handoff_upload_router.handoff_status_route(
        task_id=7,
        candidate_session=SimpleNamespace(id=3),
        db=None,
        storage_provider=SimpleNamespace(
            create_signed_download_url=lambda key,
            expires_seconds: f"https://download.example/{key}?expires={expires_seconds}"
        ),
    )
    assert result.recording is not None
    assert result.recording.recordingId == "rec_44"
    assert result.recording.status == "processing"
    assert result.recording.downloadUrl is not None
    assert result.transcript is not None
    assert result.transcript.status == "processing"
    assert result.transcript.text is None
    assert result.transcript.segments is None


@pytest.mark.asyncio
async def test_handoff_status_route_degrades_when_download_url_signing_fails(
    monkeypatch,
):
    async def _stub_status(db, *, candidate_session, task_id: int):
        del db, candidate_session, task_id
        return (
            SimpleNamespace(id=45, status="uploaded", storage_key="recordings/45.mp4"),
            None,
        )

    monkeypatch.setattr(handoff_upload_router, "get_handoff_status", _stub_status)

    def _raise_storage_error(key: str, expires_seconds: int) -> str:
        del key, expires_seconds
        raise StorageMediaError("storage down")

    result = await handoff_upload_router.handoff_status_route(
        task_id=8,
        candidate_session=SimpleNamespace(id=4),
        db=None,
        storage_provider=SimpleNamespace(
            create_signed_download_url=_raise_storage_error
        ),
    )
    assert result.recording is not None
    assert result.recording.recordingId == "rec_45"
    assert result.recording.status == "uploaded"
    assert result.recording.downloadUrl is None
    assert result.transcript is None
