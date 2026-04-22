from __future__ import annotations

import pytest

from app.config import settings
from app.integrations.storage_media import get_storage_media_provider
from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_init_success(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_FAKE_BASE_URL",
        "https://media.example.test/api/recordings/storage/fake",
    )
    get_storage_media_provider.cache_clear()
    try:
        talent_partner = await create_talent_partner(
            async_session, email="handoff-init@test.com"
        )
        sim, tasks = await create_trial(async_session, created_by=talent_partner)
        task = _handoff_task(tasks)
        candidate_session = await create_candidate_session(
            async_session,
            trial=sim,
            status="in_progress",
            with_default_schedule=True,
        )
        await async_session.commit()

        response = await async_client.post(
            f"/api/tasks/{task.id}/handoff/upload/init",
            headers=candidate_header_factory(candidate_session),
            json={
                "contentType": "video/mp4",
                "sizeBytes": 1_024,
                "filename": "demo.mp4",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["recordingId"].startswith("rec_")
        assert body["uploadUrl"].startswith(
            "https://media.example.test/api/recordings/storage/fake/upload?"
        )
        assert body["expiresInSeconds"] == 900

        recording = (
            await async_session.execute(
                select(RecordingAsset).where(RecordingAsset.task_id == task.id)
            )
        ).scalar_one()
        assert recording.status == RECORDING_ASSET_STATUS_UPLOADING
        assert recording.candidate_session_id == candidate_session.id
        assert recording.content_type == "video/mp4"
    finally:
        get_storage_media_provider.cache_clear()
