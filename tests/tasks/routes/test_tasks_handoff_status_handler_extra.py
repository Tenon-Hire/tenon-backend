from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_handoff_upload_status_handler as handler,
)


def test_resolve_download_url_suppresses_storage_errors():
    class Storage:
        def create_signed_download_url(self, *_args, **_kwargs):
            raise StorageMediaError("unavailable")

    assert (
        handler._resolve_download_url(
            Storage(), SimpleNamespace(storage_key="asset"), lambda: 60
        )
        is None
    )


@pytest.mark.asyncio
async def test_handoff_status_uses_trial_lookup_and_suppresses_recording_sign_error(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=3, trial=None, trial_id=7)
    recording = SimpleNamespace(id=11, storage_key="recording-key")
    loaded_jobs: list[tuple[int, int]] = []

    class Db:
        async def get(self, model, primary_key):
            return SimpleNamespace(company_id=17)

    class Storage:
        def create_signed_download_url(self, *_args, **_kwargs):
            raise ValueError("bad signing config")

    class Logger:
        def warning(self, *_args, **_kwargs):
            pass

    async def _load_job(db, *, company_id, recording_id):
        loaded_jobs.append((company_id, recording_id))
        return SimpleNamespace(id="job")

    monkeypatch.setattr(handler, "load_transcribe_recording_job", _load_job)

    response = await handler.handoff_status_route_impl(
        task_id=5,
        candidate_session=candidate_session,
        db=Db(),
        storage_provider=Storage(),
        recording=recording,
        transcript=None,
        transcript_job=None,
        supplemental_materials=[SimpleNamespace(storage_key="supplement")],
        is_downloadable_fn=lambda _asset: True,
        resolve_signed_url_ttl_fn=lambda: 60,
        build_transcript_status_payload_fn=lambda *_args, **_kwargs: None,
        build_recording_status_payload_fn=lambda rec, *, download_url: {
            "recordingId": str(rec.id),
            "status": "uploaded",
            "downloadUrl": download_url,
        },
        build_supplemental_status_payloads_fn=lambda assets,
        *,
        download_url_resolver: [],
        logger=Logger(),
    )

    assert loaded_jobs == [(17, 11)]
    assert response.recording.recordingId == "11"
    assert response.recording.downloadUrl is None
    assert response.supplementalMaterials == []
