from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_handoff_upload_status_handler as status_handler,
)


class _Logger:
    def __init__(self) -> None:
        self.warning_calls = 0

    def warning(self, *_args, **_kwargs) -> None:
        self.warning_calls += 1


def _build_supplemental_status_payloads(*_args, **_kwargs):
    return []


@pytest.mark.asyncio
async def test_handoff_status_route_impl_returns_transcript_without_recording():
    response = await status_handler.handoff_status_route_impl(
        task_id=22,
        candidate_session=SimpleNamespace(id=4),
        db=object(),
        storage_provider=object(),
        recording=None,
        transcript=SimpleNamespace(status="ready"),
        transcript_job=None,
        supplemental_materials=[],
        is_downloadable_fn=lambda _recording: True,
        resolve_signed_url_ttl_fn=lambda: 900,
        build_transcript_status_payload_fn=lambda transcript, transcript_job=None: {
            "status": transcript.status,
            "text": "done",
        },
        build_recording_status_payload_fn=lambda recording, download_url=None: None,
        build_supplemental_status_payloads_fn=_build_supplemental_status_payloads,
        logger=_Logger(),
    )

    assert response.recording is None
    assert response.transcript is not None
    assert response.transcript.status == "ready"
    assert response.transcript.text == "done"


@pytest.mark.asyncio
async def test_handoff_status_route_impl_skips_signing_when_recording_not_downloadable():
    logger = _Logger()

    class _StorageProvider:
        def create_signed_download_url(self, *_args, **_kwargs):
            raise AssertionError(
                "should not sign download URL for non-downloadable media"
            )

    response = await status_handler.handoff_status_route_impl(
        task_id=23,
        candidate_session=SimpleNamespace(id=5),
        db=object(),
        storage_provider=_StorageProvider(),
        recording=SimpleNamespace(
            id=8, status="processing", storage_key="recordings/key"
        ),
        transcript=None,
        transcript_job=None,
        supplemental_materials=[],
        is_downloadable_fn=lambda _recording: False,
        resolve_signed_url_ttl_fn=lambda: 900,
        build_transcript_status_payload_fn=lambda transcript, transcript_job=None: {
            "status": transcript.status
        },
        build_recording_status_payload_fn=lambda recording, download_url=None: {
            "recordingId": f"rec_{recording.id}",
            "status": recording.status,
            "downloadUrl": download_url,
        },
        build_supplemental_status_payloads_fn=_build_supplemental_status_payloads,
        logger=logger,
    )

    assert response.recording is not None
    assert response.recording.recordingId == "rec_8"
    assert response.recording.downloadUrl is None
    assert response.transcript is None
    assert logger.warning_calls == 0
