from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_handoff_upload_routes as handoff_upload_router,
)


@pytest.mark.asyncio
async def test_handoff_status_route_serializes_ready_transcript_segments(monkeypatch):
    async def _stub_status(db, *, candidate_session, task_id: int):
        del db, candidate_session, task_id
        return (
            SimpleNamespace(id=46, status="uploaded", storage_key="recordings/46.mp4"),
            SimpleNamespace(
                status="ready",
                text="hello world",
                segments_json=[
                    {"id": 7, "startMs": "10", "endMs": 20.9, "text": "first"},
                    {"startMs": None, "endMs": True, "text": "second"},
                    {"startMs": 5},
                    "bad-segment",
                ],
            ),
        )

    monkeypatch.setattr(handoff_upload_router, "get_handoff_status", _stub_status)
    result = await handoff_upload_router.handoff_status_route(
        task_id=9,
        candidate_session=SimpleNamespace(id=5),
        db=None,
        storage_provider=SimpleNamespace(
            create_signed_download_url=lambda key,
            expires_seconds: f"https://download.example/{key}?expires={expires_seconds}"
        ),
    )
    assert result.transcript is not None
    assert result.transcript.status == "ready"
    assert result.transcript.text == "hello world"
    assert result.transcript.segments is not None
    assert [
        segment.model_dump(exclude_none=True) for segment in result.transcript.segments
    ] == [
        {"id": "7", "startMs": 10, "endMs": 20, "text": "first"},
        {"text": "second"},
    ]
