from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.routers.tasks import handoff_upload as handoff_upload_router
from app.schemas.submissions import (
    HandoffUploadCompleteRequest,
    HandoffUploadInitRequest,
)


@pytest.mark.asyncio
async def test_init_handoff_upload_route_shapes_response(monkeypatch):
    async def _stub_init(
        db,
        *,
        candidate_session,
        task_id: int,
        content_type: str,
        size_bytes: int,
        filename: str | None,
        storage_provider,
    ):
        del db, candidate_session, task_id, content_type, size_bytes, filename
        del storage_provider
        return SimpleNamespace(id=12), "https://upload.example/signed", 900

    monkeypatch.setattr(handoff_upload_router, "init_handoff_upload", _stub_init)

    result = await handoff_upload_router.init_handoff_upload_route(
        task_id=7,
        payload=HandoffUploadInitRequest(
            contentType="video/mp4",
            sizeBytes=1234,
            filename="demo.mp4",
        ),
        candidate_session=SimpleNamespace(id=3),
        db=None,
        storage_provider=SimpleNamespace(),
    )

    assert result.recordingId == "rec_12"
    assert result.uploadUrl == "https://upload.example/signed"
    assert result.expiresInSeconds == 900


@pytest.mark.asyncio
async def test_complete_handoff_upload_route_shapes_response(monkeypatch):
    async def _stub_complete(
        db,
        *,
        candidate_session,
        task_id: int,
        recording_id_value: str,
        storage_provider,
    ):
        del db, candidate_session, task_id, recording_id_value, storage_provider
        return SimpleNamespace(id=33, status="uploaded")

    monkeypatch.setattr(
        handoff_upload_router, "complete_handoff_upload", _stub_complete
    )

    result = await handoff_upload_router.complete_handoff_upload_route(
        task_id=7,
        payload=HandoffUploadCompleteRequest(recordingId="rec_33"),
        candidate_session=SimpleNamespace(id=3),
        db=None,
        storage_provider=SimpleNamespace(),
    )

    assert result.recordingId == "rec_33"
    assert result.status == "uploaded"


@pytest.mark.asyncio
async def test_handoff_status_route_shapes_response(monkeypatch):
    async def _stub_status(
        db,
        *,
        candidate_session,
        task_id: int,
    ):
        del db, candidate_session, task_id
        return (
            SimpleNamespace(id=44, status="processing"),
            SimpleNamespace(status="processing"),
        )

    monkeypatch.setattr(handoff_upload_router, "get_handoff_status", _stub_status)

    result = await handoff_upload_router.handoff_status_route(
        task_id=7,
        candidate_session=SimpleNamespace(id=3),
        db=None,
    )

    assert result.recording is not None
    assert result.recording.recordingId == "rec_44"
    assert result.recording.status == "processing"
    assert result.transcript is not None
    assert result.transcript.status == "processing"
