from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_delete_recording_asset_disabled_and_missing_recording(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="privacy-delete-disabled@test.com",
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(async_session, trial=sim)

    monkeypatch.setattr(settings.storage_media, "MEDIA_DELETE_ENABLED", False)
    with pytest.raises(HTTPException) as disabled_exc:
        await delete_recording_asset(
            async_session,
            recording_id=123,
            candidate_session=candidate_session,
        )
    assert disabled_exc.value.status_code == 403

    monkeypatch.setattr(settings.storage_media, "MEDIA_DELETE_ENABLED", True)
    with pytest.raises(HTTPException) as missing_exc:
        await delete_recording_asset(
            async_session,
            recording_id=123,
            candidate_session=candidate_session,
        )
    assert missing_exc.value.status_code == 404
